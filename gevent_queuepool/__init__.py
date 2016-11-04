#coding=utf-8
def load():
    try:
        from sqlalchemy import pool
        from .greenlet_queuepool import GreenletQueuePool
        setattr(pool, "GreenletQueuePool", GreenletQueuePool)
    except Exception, e:
        print e