import hashlib
import pytz

utc = pytz.timezone('UTC')


def dthandler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError('Object of type {} with value of {} is not JSON'
                        'serializable'.format(type(obj), repr(obj)))


class Subscriber(object):

    def __init__(self, config=None, state=None):
        self.config = config
        self.state = state
        self.count_seen = 0
        self.count_older = 0

    def seen(self, item):
        # this is an effort to make sure that a dictionary with the
        # same key/value pairs always produces the same string representation
        # (by its elements by key):
        string_rep = '{}'.format(sorted(item.items()))
        m = hashlib.md5()
        m.update(string_rep)
        hash = m.hexdigest()

        if hash in self.state:
            self.count_seen += 1
            return True
        self.state[hash] = item
        return False
