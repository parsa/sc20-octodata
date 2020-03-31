import re
from decimal import Decimal

import rcb12_term.helpers as h


def main():
    files = h.list_txt_files_in_cur_dir('*.txt.xz')
    for target in files:
        hpx_out = h.read_file(target)

        dec_val_regex = re.compile(r'\d+(?:\.\d+)?')
        nums = [Decimal(i[0]) for i in dec_val_regex.finditer(hpx_out)]
        print('Numbers extracted: {:,}'.format(len(nums)))

        lim1 = 2 ** 16
        lim2 = 2 ** 15

        num1 = [i for i in nums if i > lim1]
        print('Numbers larger that 2**16: {:,}'.format(len(num1)))
        num2 = [i for i in nums if i > lim2]
        print('Numbers larger that 2**15: {:,}'.format(len(num2)))

        gre = re.compile(
            r'/(?:[^{\n]+)\{locality#(?:\d+)'
            r'/(?:(?:(?:pool#[^/\n]+/[^#\n]+)'
            r'#(?:\d+))|(?:[^}\n]+))\}'
            r'/(?:[^@\n]+)(?:@(?:.+))?'
            r'(?:,[^,\n]*])*')

        def filter_value_unit_pairs(hpx_cout):
            for i in gre.finditer(hpx_out):
                counterline_parts = i[0].split(',')
                yield counterline_parts[4:], counterline_parts[0]
        for i, o in filter_value_unit_pairs(hpx_out):
            if not o.endswith('count/cumulative-phases') and \
                not o.endswith('count/cumulative') and \
                not o.startswith('/agas{locality') and \
                    Decimal(i[0]) > Decimal(2 ** 16):
                print(i, o)
