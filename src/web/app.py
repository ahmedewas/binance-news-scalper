"""Authenticated dashboard API; reads never call exchange network endpoints."""
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from src.config import config


class ActiveRequest(BaseModel):
    active: bool


class CloseRequest(BaseModel):
    symbol: str = Field(min_length=3, max_length=30, pattern=r'^[A-Z0-9]+/USDT$')


class ResetRequest(BaseModel):
    confirmation: str


class ModeRequest(BaseModel):
    mode: str = Field(pattern='^(PAPER|LIVE)$')


def create_app(worker, dashboard_token=None):
    app = FastAPI(title='Binance Scalper', docs_url=None, redoc_url=None, openapi_url=None)
    token = config.dashboard_token if dashboard_token is None else dashboard_token
    static_dir = Path(__file__).parent / 'static'
    app.mount('/static', StaticFiles(directory=static_dir), name='static')

    @app.middleware('http')
    async def protect(request: Request, call_next):
        if request.url.path.startswith('/api/'):
            if token:
                supplied = request.headers.get('X-Dashboard-Token', '')
                if not secrets.compare_digest(supplied.encode(), token.encode()):
                    return JSONResponse({'detail':'أدخل رمز لوحة التحكم الصحيح'}, status_code=401)
            elif request.url.hostname not in {'127.0.0.1','localhost','::1','testserver'}:
                return JSONResponse({'detail':'الوصول عن بعد يحتاج DASHBOARD_TOKEN'}, status_code=403)
            if request.method == 'POST':
                if request.headers.get('X-Requested-With') != 'ScalperDashboard':
                    return JSONResponse({'detail':'طلب التحكم غير موثوق'}, status_code=403)
                origin = request.headers.get('origin')
                if origin and urlsplit(origin).netloc != request.headers.get('host'):
                    return JSONResponse({'detail':'المصدر غير مسموح'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @app.get('/')
    def index():
        return FileResponse(static_dir / 'index.html')

    @app.get('/api/status')
    def status():
        return worker.snapshot()

    @app.post('/api/active')
    def active(payload: ActiveRequest):
        try:
            return worker.set_active(payload.active)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post('/api/mode')
    def set_mode(payload: ModeRequest):
        try:
            return worker.switch_mode(payload.mode)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post('/api/toggle')
    def toggle():
        with worker.lock:
            return active(ActiveRequest(active=not worker.is_active))

    @app.post('/api/close')
    def close(payload: CloseRequest):
        result = worker.close_position(payload.symbol)
        if not result['success']:
            return JSONResponse({'detail': result['message'], **result}, status_code=409)
        return result

    @app.post('/api/close_all')
    def close_all():
        return worker.close_all()

    @app.post('/api/reconcile')
    def reconcile():
        return worker.reconcile_pending()

    @app.post('/api/paper/reset')
    def reset(payload: ResetRequest):
        if payload.confirmation != 'RESET PAPER':
            raise HTTPException(400, 'تأكيد بدء جلسة ورقية جديدة مطلوب')
        try:
            return worker.reset_paper_session()
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get('/api/journal')
    def journal():
        return {'journal': worker.journal.read_journal()}

    @app.get('/api/autopsy')
    def autopsy():
        from src.core.session_autopsy import SessionAutopsy
        return SessionAutopsy.analyze_session(getattr(worker, 'trade_history', []))

    @app.get('/healthz')
    def health():
        state = worker.snapshot()
        return {'status':'running', 'last_step': state.get('health',{}).get('last_step')}

    return app
