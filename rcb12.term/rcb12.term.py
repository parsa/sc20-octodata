#!/usr/bin/env python3

import os
import glob
import re
import pandas as pd


def get_pfx_counter_line_pattern():
    return re.compile(
        r'^/[^{]+\{[^}]+\}/([^,]+,){4,5}[^,\n]+$', re.MULTILINE)


def test_pfx_counter_line_pattern(pattern):
    def test_case(subject):
        return [i.group() for i in pattern.finditer(subject)]

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
        '/threads{locality#0/pool#default/worker-thread#3}/count/cumulative,44,154828.262962,[s],1.04786e+08'
    ]

    assert test_case(subject) == expected


def get_general_counter_form_pattern():
    return re.compile(
        r'/(?P<object>[^{]+)\{locality#(?P<locality>\d+)/(?:(?:(?P<instance1>pool#[^/]+/[^#]+)#(?P<thread_id>\d+))|(?P<instance2>[^}]+))\}/(?P<counter>[^@]+)(?:@(?P<params>.+))?')


def test_general_counter_form_pattern(pattern):
    def test_case(subject):
        m = pattern.match(subject)
        assert m is not None
        return m.groupdict()

    assert test_case('/threads{locality#0/pool#default/worker-thread#0}/count/cumulative') == {
        'object': 'threads',
        'locality': '0',
        'instance1': 'pool#default/worker-thread',
        'thread_id': '0',
        'instance2': None,
        'counter': 'count/cumulative',
        'params': None}
    assert test_case('/threads{locality#61/total/total}/count/cumulative,44,154828.184221,[s],2.28135e+09') == {
        'object': 'threads',
        'locality': '61',
        'instance1': None,
        'thread_id': None,
        'instance2': 'total/total',
        'counter': 'count/cumulative,44,154828.184221,[s],2.28135e+09',
        'params': None}


def read_file(filepath):
    assert os.access(filepath, os.R_OK)

    # Read one file for testing
    with open(filepath, 'r') as hpx_output_handle:
        hpx_output = hpx_output_handle.read()
    return hpx_output


def extract_counters_df(hpx_output):
    assert isinstance(hpx_output, str)

    all_counters = []
    for pfx_counter_line in pfx_counter_line_pattern.finditer(hpx_output):
        raw_line = pfx_counter_line.group(0)
        line_split = raw_line.split(',')

        def justify_fields(line_split):
            if len(line_split) == 5:
                # unit for count values
                line_split += ('1')
            assert len(line_split) == 6
        justify_fields(line_split)

        raw_general_name = line_split[0]
        split_general_form = general_counter_form_pattern.match(
            raw_general_name)
        assert split_general_form is not None

        countername_groups = split_general_form.groupdict()

        def unify_instance_field(countername_groups):
            if countername_groups['instance1'] is not None:
                countername_groups['instance'] = countername_groups['instance1']
            else:
                countername_groups['instance'] = countername_groups['instance2']

            del countername_groups['instance1']
            del countername_groups['instance2']
        unify_instance_field(countername_groups)

        all_counters += [(
            countername_groups["object"],
            countername_groups["locality"],
            countername_groups["instance"],
            countername_groups["counter"],
            countername_groups["thread_id"],
            countername_groups["params"],
        ) + tuple(line_split)]

    df = pd.DataFrame(all_counters, columns=[
        'objectname', 'locality', 'instance', 'countername', 'thread_id',
        'parameters', 'general_form', 'iteration', 'timestamp',
        'timestamp_unit', 'value', 'unit'])
    assert isinstance(df, pd.DataFrame)
    assert len(df) != 0
    return df


def check_and_prune_fields(df):
    assert isinstance(df, pd.DataFrame)

    def fix_units(df):
        df.locality = pd.to_numeric(df.locality, downcast='unsigned')
        df.iteration = pd.to_numeric(df.iteration, downcast='unsigned')
        df.timestamp = pd.to_numeric(df.timestamp)
        df.value = pd.to_numeric(df.value)
        df.thread_id = pd.to_numeric(df.thread_id, downcast='unsigned')
        df.loc[df.countername == 'idle-rate', 'value'] *= 0.01
    fix_units(df)

    def drop_irrelevant_counters(df):
        # drop AGAS results
        df = df.loc[df.objectname != 'agas']
        # drop threads...pool#default/worker-thread...count/cumulative-phases
        df = df.loc[df.countername != 'count/cumulative-phases']
        df = df.loc[df.countername != 'count/cumulative']
    drop_irrelevant_counters(df)

    # units can only be [0.01%], 1, [s], and [ns]
    def check_all_data_units(df):
        x = df.loc[(df.unit != '1')]
        x = x.loc[x.unit != '[0.01%]']
        x = x.loc[x.unit != '[s]']
        x = x.loc[x.unit != '[ns]']
        assert len(x) == 0

    check_all_data_units(df)

    def remove_unused_columns(df):
        # no parameters are expected
        assert len(df.loc[~df.parameters.isnull()]) == 0
        del df['parameters']

        del df['timestamp_unit']
        del df['unit']
        del df['timestamp']
        del df['general_form']
    remove_unused_columns(df)


def process_df(df):
    def get_octotiger_counters(df):
        octo_pivot = df.pivot_table(
            index=[
                'iteration',
                'locality'],
            columns=['countername'],
            values='value',
            dropna=False)
        del octo_pivot['idle-rate']
        return octo_pivot
    octotiger_counters = get_octotiger_counters(df)

    def get_idle_rate_counters(df):
        idle_rate_pivot = df.pivot_table(
            index=[
                'iteration',
                'locality'],
            columns=['thread_id'],
            values='value')
        return idle_rate_pivot
    idle_rates = get_idle_rate_counters(df)

    result = pd.concat([octotiger_counters, idle_rates], axis=1)
    return result


# Counter line search and counter name parsing regex patterns
pfx_counter_line_pattern = get_pfx_counter_line_pattern()
general_counter_form_pattern = get_general_counter_form_pattern()


class step_block(object):
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        print(self.msg)

    def __exit__(self, type, value, tb):
        print('done', self.msg)


def main():
    with step_block('checking regex patterns integrity'):
        test_general_counter_form_pattern(general_counter_form_pattern)
        test_pfx_counter_line_pattern(pfx_counter_line_pattern)

    with step_block('listing *.txt files in current directory'):
        hpx_output_files = glob.glob('*.txt')
        assert isinstance(hpx_output_files, list)
        assert len(hpx_output_files) >= 1

    for rf in hpx_output_files:
        print(80 * '=')
        print('subject:', rf)
        print(80 * '-')

        r0f = os.path.join(os.curdir, rf)
        with step_block('reading ' + r0f):
            hpx_out = read_file(r0f)

        with step_block('extracing performance counter lines'):
            df = extract_counters_df(hpx_out)

        with step_block('pruning fields'):
            check_and_prune_fields(df)

        with step_block('extracing values'):
            df = process_df(df)

        def get_csv_output_path(original_path):
            return os.path.splitext(original_path)[0] + '.csv'
        of = get_csv_output_path(rf)

        with step_block('writing to ' + of):
            df.to_csv(of)


if __name__ == '__main__':
    main()
