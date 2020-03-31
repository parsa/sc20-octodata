import unittest
import rcb12_term.patterns


class main_test(unittest.TestCase):
    def test_general_counter_form_pattern(self):
        pattern = rcb12_term.patterns.get_general_counter_form_pattern()

        def get_actual(subject):
            m = pattern.match(subject)
            self.assertIsNotNone(m)
            return m.groupdict()

        self.assertEqual({
            'object': 'threads',
            'locality': '0',
            'instance1': 'pool#default/worker-thread',
            'thread_id': '0',
            'instance2': None,
            'counter': 'count/cumulative',
            'params': None},
            get_actual('/threads{locality#0/pool#default/worker-thread#0}/count/cumulative'))
        self.assertEqual({
            'object': 'threads',
            'locality': '61',
            'instance1': None,
            'thread_id': None,
            'instance2': 'total/total',
            'counter': 'count/cumulative,44,154828.184221,[s],2.28135e+09',
            'params': None},
            get_actual('/threads{locality#61/total/total}/count/cumulative,44,154828.184221,[s],2.28135e+09'))

    def test_pfx_counter_line_pattern(self):
        pattern = rcb12_term.patterns.get_pfx_counter_line_pattern()

        def get_actual(subject):
            r = pattern.finditer(subject)
            return [i[0] for i in r]

        subject = '''
/octotiger{locality#0/total}/subgrid_leaves,2,3602.438779,[s],32428
/octotiger{locality#1/total}/subgrid_leaves,2,3602.428582,[s],34118
/octotiger{locality#2/total}/subgrid_leaves,2,3602.430246,[s],33918
/octotiger{locality#3/total}/subgrid_leaves,2,3602.431576,[s],34443
/octotiger{locality#4/total}/subgrid_leaves,2,3602.436175,[s],33173
/threads{locality#59/total/total}/count/cumulative,44,154828.198473,[s],2.3065e+09
/threads{locality#60/total/total}/count/cumulative,44,154828.221342,[s],2.24724e+09
/threads{locality#61/total/total}/count/cumulative,44,154828.184221,[s],2.28135e+09
/threads{locality#62/total/total}/count/cumulative,44,154828.221351,[s],2.20491e+09
/threads{locality#63/total/total}/count/cumulative,44,154828.216028,[s],2.05324e+09
/threads{locality#0/pool#default/worker-thread#0}/count/cumulative,44,154828.257432,[s],1.14378e+08
/threads{locality#0/pool#default/worker-thread#1}/count/cumulative,44,154828.260203,[s],1.05219e+08
/threads{locality#0/pool#default/worker-thread#2}/count/cumulative,44,154828.262954,[s],1.04616e+08
/threads{locality#0/pool#default/worker-thread#3}/count/cumulative,44,154828.262962,[s],1.04786e+08
'''
        expected = [
            '/octotiger{locality#0/total}/subgrid_leaves,2,3602.438779,[s],32428',
            '/octotiger{locality#1/total}/subgrid_leaves,2,3602.428582,[s],34118',
            '/octotiger{locality#2/total}/subgrid_leaves,2,3602.430246,[s],33918',
            '/octotiger{locality#3/total}/subgrid_leaves,2,3602.431576,[s],34443',
            '/octotiger{locality#4/total}/subgrid_leaves,2,3602.436175,[s],33173',
            '/threads{locality#59/total/total}/count/cumulative,44,154828.198473,[s],2.3065e+09',
            '/threads{locality#60/total/total}/count/cumulative,44,154828.221342,[s],2.24724e+09',
            '/threads{locality#61/total/total}/count/cumulative,44,154828.184221,[s],2.28135e+09',
            '/threads{locality#62/total/total}/count/cumulative,44,154828.221351,[s],2.20491e+09',
            '/threads{locality#63/total/total}/count/cumulative,44,154828.216028,[s],2.05324e+09',
            '/threads{locality#0/pool#default/worker-thread#0}/count/cumulative,44,154828.257432,[s],1.14378e+08',
            '/threads{locality#0/pool#default/worker-thread#1}/count/cumulative,44,154828.260203,[s],1.05219e+08',
            '/threads{locality#0/pool#default/worker-thread#2}/count/cumulative,44,154828.262954,[s],1.04616e+08',
            '/threads{locality#0/pool#default/worker-thread#3}/count/cumulative,44,154828.262962,[s],1.04786e+08',
        ]

        self.assertEqual(get_actual(subject), expected)


if __name__ == '__main__':
    unittest.main()
