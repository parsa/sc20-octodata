import re


dec_val_regex = re.compile(
    r'^(/[^,\n]+)(,[^,\n]+){4,5}$', re.MULTILINE
)


def generator(hpx_out):
    for i in dec_val_regex.finditer(hpx_out):
        yield i[0] + '\n'


class generator_reader(object):
    def __init__(self, hpx_out):
        self.hpx_out = hpx_out
        self.gen = generator(self.hpx_out)

    def __iter__(self):
        return self

    def read(self, n=0):
        try:
            return next(self.gen)
        except StopIteration:
            return ''
