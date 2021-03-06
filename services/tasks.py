from __future__ import unicode_literals

import logging

from alliance_auth.celeryapp import app

from services.hooks import ServicesHook
import redis

REDIS_CLIENT = redis.Redis()

logger = logging.getLogger(__name__)


# http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html
def only_one(function=None, key="", timeout=None):
    """Enforce only one celery task at a time."""

    def _dec(run_func):
        """Decorator."""

        def _caller(*args, **kwargs):
            """Caller."""
            ret_value = None
            have_lock = False
            lock = REDIS_CLIENT.lock(key, timeout=timeout)
            try:
                have_lock = lock.acquire(blocking=False)
                if have_lock:
                    ret_value = run_func(*args, **kwargs)
            finally:
                if have_lock:
                    lock.release()

            return ret_value

        return _caller

    return _dec(function) if function is not None else _dec


@app.task(bind=True)
def validate_services(self, user):
    logger.debug('Ensuring user %s has permissions for active services'.format(user))
    # Iterate through services hooks and have them check the validity of the user
    for svc in ServicesHook.get_services():
        try:
            svc.validate_user(user)
        except:
            logger.exception('Exception running validate_user for services module %s on user %s' % (svc, user))
