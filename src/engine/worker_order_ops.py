"""Worker Order Operations: Manages exit executions, manual closes and order reconciliations."""
import uuid
import math
from datetime import datetime, timezone
from src.core.models import Position
from src.engine.position_handler import PositionHandler


class WorkerOrderOpsMixin:
    def _before_order(self, symbol: str, side: str, quantity: float) -> str:
        if self.storage_failed:
            raise RuntimeError('State storage unavailable')
        cid = 'sc-' + uuid.uuid4().hex[:28]
        self.pending_orders[cid] = dict(symbol=symbol, side=side, quantity=quantity, created_at=datetime.now(timezone.utc).isoformat())
        self.persist()
        return cid

    def _after_order(self, cid: str, order) -> None:
        if order.status == 'UNKNOWN':
            self.is_active = False
            self.pending_orders[cid]['order_id'] = order.order_id
            self.error('نتيجة أمر غير محسومة؛ يلزم مطابقة الأمر مع البورصة قبل الاستئناف')
        else:
            self.pending_orders.pop(cid, None)
        self.persist()

    def _exit(self, symbol: str, reason: str, ratio: float = 1.0) -> dict:
        if symbol not in self.positions:
            return dict(success=False, symbol=symbol, message='المركز غير موجود', status='NOT_FOUND')
        if self.positions[symbol].execution_uncertain:
            return dict(success=False, symbol=symbol, message='الأمر غير محسوم؛ يلزم مطابقته', status='UNKNOWN')
        cid = self._before_order(symbol, 'SELL', self.positions[symbol].amount * ratio)
        result = PositionHandler.execute_exit(self.exchange, self.positions, symbol, reason, ratio, self.trade_history, client_order_id=cid)
        if result['status'] == 'UNKNOWN':
            self.is_active = False
            self.pending_orders[cid]['order_id'] = result.get('order_id', '')
            self.error(result['message'])
        else:
            self.pending_orders.pop(cid, None)
        if result.get('trade'):
            self._record(result['trade'])
        else:
            self.persist()
            if not result['success']:
                self.error(result['message'])
        self.cash = self.exchange.get_balance('USDT')
        return result

    def close_position(self, symbol: str) -> dict:
        with self.lock:
            result = self._exit(symbol, 'MANUAL_CLOSE')
            self._publish()
            return result

    def close_all(self) -> dict:
        with self.lock:
            self.is_active = False
            self.persist()
            results = [self._exit(s, 'MANUAL_CLOSE') for s in list(self.positions)]
            self._publish()
            return dict(status='ALL_POSITIONS_CLOSED' if not self.positions else 'PARTIAL_FAILURE',
                        results=results, remaining=list(self.positions), is_active=False)

    def reconcile_pending(self) -> dict:
        with self.lock:
            results, self.is_active = [], False
            for cid, intent in list(self.pending_orders.items()):
                order = self.exchange.reconcile_order(intent['symbol'], cid)
                if order.status == 'UNKNOWN':
                    results.append(dict(id=cid, success=False, message=order.message))
                    continue
                v_fill = (order.success and order.status == 'FILLED' and order.symbol == intent['symbol'] and
                          order.side == intent['side'] and bool(order.order_id) and (not order.client_order_id or order.client_order_id == cid) and
                          all(math.isfinite(v) and v > 0 for v in (order.price, order.amount, order.cost)) and
                          all(math.isfinite(v) and v >= 0 for v in (order.fee_quote, order.fee_base)))
                v_rej = (not order.success and order.status == 'REJECTED' and order.amount == 0 and
                         order.symbol == intent['symbol'] and order.side == intent['side'] and (not order.client_order_id or order.client_order_id == cid))
                if not (v_fill or v_rej):
                    results.append(dict(id=cid, success=False, message='نتيجة مطابقة غير صالحة؛ بقي الأمر معلقاً للفحص'))
                    continue
                sym = intent['symbol']
                if order.success and intent['side'] == 'BUY':
                    if sym in self.positions:
                        results.append(dict(id=cid, success=False, message='المركز موجود؛ يلزم فحص يدوي'))
                        continue
                    slots = {p.slot_id for p in self.positions.values()}
                    slot = next((i for i in range(1, self.allocator.max_slots + 1) if i not in slots), None)
                    if slot is None:
                        results.append(dict(id=cid, success=False, message='لا توجد خانة لتسوية المركز'))
                        continue
                    self.positions[sym] = Position(sym, order.price, order.price, order.amount, order.price,
                                                   datetime.fromisoformat(intent['created_at']), slot, cost_basis=order.cost + order.fee_quote)
                elif order.success:
                    result = PositionHandler.apply_fill(self.positions, sym, 'RECONCILED_EXIT', order, self.trade_history)
                    if not result['success']:
                        results.append(dict(id=cid, success=False, message=result['message']))
                        continue
                    self.pending_orders.pop(cid, None)
                    self._record(result['trade'])
                elif sym in self.positions:
                    self.positions[sym].execution_uncertain = False
                self.pending_orders.pop(cid, None)
                self.persist()
                results.append(dict(id=cid, success=True, message='تمت مطابقة حالة الأمر'))
            self.cash, _ = self.exchange.get_balance('USDT'), self._publish()
            return {'results': results, 'remaining': len(self.pending_orders), 'is_active': False}
