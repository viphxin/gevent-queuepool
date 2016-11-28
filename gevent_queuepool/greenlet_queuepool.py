#coding=utf-8
"""
支持gevent 最新版本的线程池
"""
from gevent.lock import Semaphore
from gevent.queue import Queue, Empty, Full
from sqlalchemy.pool import Pool
from sqlalchemy import exc

class Singleton(type):
    """Singleton Metaclass"""

    def __init__(self, name, bases, dic):
        super(Singleton, self).__init__(name, bases, dic)
        self.instance = None

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = super(Singleton, self).__call__(*args, **kwargs)
        return self.instance

class GreenletQueuePool(Pool):

    """A :class:`.Pool` that imposes a limit on the number of open connections.

    :class:`.QueuePool` is the default pooling implementation used for
    all :class:`.Engine` objects, unless the SQLite dialect is in use.

    """
    __metaclass__ = Singleton

    def __init__(self, creator, pool_size=5, max_overflow=10, timeout=30,
                 **kw):
        """
        Construct a QueuePool.

        :param creator: a callable function that returns a DB-API
          connection object, same as that of :paramref:`.Pool.creator`.

        :param pool_size: The size of the pool to be maintained,
          defaults to 5. This is the largest number of connections that
          will be kept persistently in the pool. Note that the pool
          begins with no connections; once this number of connections
          is requested, that number of connections will remain.
          ``pool_size`` can be set to 0 to indicate no size limit; to
          disable pooling, use a :class:`~sqlalchemy.pool.NullPool`
          instead.

        :param max_overflow: The maximum overflow size of the
          pool. When the number of checked-out connections reaches the
          size set in pool_size, additional connections will be
          returned up to this limit. When those additional connections
          are returned to the pool, they are disconnected and
          discarded. It follows then that the total number of
          simultaneous connections the pool will allow is pool_size +
          `max_overflow`, and the total number of "sleeping"
          connections the pool will allow is pool_size. `max_overflow`
          can be set to -1 to indicate no overflow limit; no limit
          will be placed on the total number of concurrent
          connections. Defaults to 10.

        :param timeout: The number of seconds to wait before giving up
          on returning a connection. Defaults to 30.

        :param \**kw: Other keyword arguments including
          :paramref:`.Pool.recycle`, :paramref:`.Pool.echo`,
          :paramref:`.Pool.reset_on_return` and others are passed to the
          :class:`.Pool` constructor.

        """
        Pool.__init__(self, creator, **kw)
        self._pool = Queue(pool_size)
        self._overflow = 0 - pool_size
        self._max_overflow = max_overflow
        self._timeout = timeout
        self._overflow_lock = Semaphore()

    def _do_return_conn(self, conn):
        try:
            # print 'return'*30
            # print self._pool.qsize()
            self._pool.put(conn, False)
        except Full:
            # print 'full'*30
            try:
                conn.close()
            finally:
                self._dec_overflow()

    def _do_get(self):
        # print 'get'*30
        # print self._pool.qsize()
        use_overflow = self._max_overflow > -1

        try:
            wait = use_overflow and self._overflow >= self._max_overflow
            return self._pool.get(wait, self._timeout)
        except Empty:
            if use_overflow and self._overflow >= self._max_overflow:
                if not wait:
                    return self._do_get()
                else:
                    raise exc.TimeoutError(
                        "GreenletQueuePool limit of size %d overflow %d reached, "
                        "connection timed out, timeout %d" %
                        (self.size(), self.overflow(), self._timeout))

            if self._inc_overflow():
                try:
                    return self._create_connection()
                except:
                    self._dec_overflow()
            else:
                return self._do_get()

    def _inc_overflow(self):
        if self._max_overflow == -1:
            self._overflow += 1
            return True
        with self._overflow_lock:
            if self._overflow < self._max_overflow:
                self._overflow += 1
                return True
            else:
                return False

    def _dec_overflow(self):
        with self._overflow_lock:
            if self._max_overflow == -1:
                self._overflow -= 1
                return True
            else:
                self._overflow -= 1
                return True

    def recreate(self):
        self.logger.info("Pool recreating")
        return self.__class__(self._creator, pool_size=self._pool.maxsize,
                              max_overflow=self._max_overflow,
                              timeout=self._timeout,
                              recycle=self._recycle, echo=self.echo,
                              logging_name=self._orig_logging_name,
                              use_threadlocal=self._use_threadlocal,
                              reset_on_return=self._reset_on_return,
                              _dispatch=self.dispatch,
                              _dialect=self._dialect)

    def dispose(self):
        while True:
            try:
                conn = self._pool.get(False)
                conn.close()
            except Empty:
                break

        self._overflow = 0 - self.size()
        self.logger.info("Pool disposed. %s", self.status())

    def status(self):
        return "Pool size: %d  Connections in pool: %d "\
            "Current Overflow: %d Current Checked out "\
            "connections: %d" % (self.size(),
                                 self.checkedin(),
                                 self.overflow(),
                                 self.checkedout())

    def size(self):
        return self._pool.maxsize

    def checkedin(self):
        return self._pool.qsize()

    def overflow(self):
        return self._overflow

    def checkedout(self):
        return self._pool.maxsize - self._pool.qsize() + self._overflow