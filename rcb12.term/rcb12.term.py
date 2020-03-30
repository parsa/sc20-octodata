#!/usr/bin/env python3

import concurrent.futures
import glob
import lzma
import os
import pathlib
import re

import pandas as pd
from tqdm import tqdm


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
    with lzma.open(filepath, 'rt', encoding='utf-8') as hpx_output_handle:
        hpx_output = hpx_output_handle.read()
    return hpx_output


def extract_counter_lines(hpx_output, pfx_counter_line_pattern):
    assert isinstance(hpx_output, str)

    for pfx_counter_line in pfx_counter_line_pattern.finditer(hpx_output):
        raw_line = pfx_counter_line.group(0)

        line_segments = raw_line.split(',')

        def justify_fields(segments):
            if len(segments) == 5:
                # unit for count values
                segments += ('1')
            assert len(segments) == 6
        justify_fields(line_segments)

        yield line_segments


def process_counters(lines, general_counter_form_pattern):
    for segments in lines:
        general_form = segments[0]
        general_form_m = general_counter_form_pattern.match(
            general_form)
        assert general_form_m is not None

        value_group_dict = general_form_m.groupdict()

        def unify_instance_field(groups):
            if groups['instance1'] is not None:
                groups['instance'] = groups['instance1']
            else:
                groups['instance'] = groups['instance2']

            del groups['instance1']
            del groups['instance2']
        unify_instance_field(value_group_dict)

        yield (
            value_group_dict["object"],
            value_group_dict["locality"],
            value_group_dict["instance"],
            value_group_dict["counter"],
            value_group_dict["thread_id"],
            value_group_dict["params"],
        ) + tuple(segments)


def check_and_prune_fields(df):
    def fix_units(df):
        df.locality = pd.to_numeric(df.locality, downcast='unsigned')
        df.iteration = pd.to_numeric(df.iteration, downcast='unsigned')
        df.timestamp = pd.to_numeric(df.timestamp)
        df.value = pd.to_numeric(df.value)
        df.thread_id = pd.to_numeric(df.thread_id, downcast='unsigned')
        df.loc[df.countername == 'idle-rate', 'value'] *= 0.01

    def drop_irrelevant_counters(df):
        def drop_values(column, value):
            df.drop(df.index[df[column] == value], inplace=True)
        # drop AGAS results
        drop_values('objectname', 'agas')
        # drop threads...pool#default/worker-thread...count/cumulative-phases
        drop_values('countername', 'count/cumulative-phases')
        drop_values('countername', 'count/cumulative')

    # units can only be [0.01%], 1, [s], and [ns]
    def check_all_data_units(df):
        x = df.loc[(df.unit != '1')]
        x = x.loc[x.unit != '[0.01%]']
        x = x.loc[x.unit != '[s]']
        x = x.loc[x.unit != '[ns]']
        assert len(x) == 0

    def remove_unused_columns(df):
        # no parameters are expected
        assert len(df.loc[~df.parameters.isnull()]) == 0
        del df['parameters']

        del df['timestamp_unit']
        del df['unit']
        del df['timestamp']
        del df['general_form']

    assert isinstance(df, pd.DataFrame)

    fix_units(df)
    drop_irrelevant_counters(df)
    check_all_data_units(df)
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


def process_file(rf, counter_line_pattern, counter_form_pattern, pc):
    r0f = os.path.join(os.curdir, rf)
    pc.set_description('Reading')
    hpx_out = read_file(r0f)
    pc.update()

    pc.set_description('Extracting counters')
    line_gen = extract_counter_lines(hpx_out, counter_line_pattern)
    pc.update()

    pc.set_description('Processing counters')
    col_gen = process_counters(line_gen, counter_form_pattern)
    vals = list(col_gen)
    pc.update()

    pc.set_description('Assembling dataframe')
    df = pd.DataFrame(vals, columns=[
        'objectname', 'locality', 'instance', 'countername',
        'thread_id', 'parameters', 'general_form', 'iteration',
        'timestamp', 'timestamp_unit', 'value', 'unit'])
    pc.update()

    pc.set_description('Pruning fields')
    check_and_prune_fields(df)
    pc.update()

    pc.set_description('Extracting values')
    vdf = process_df(df)
    pc.update()

    def get_csv_output_path(original_path):
        return str(pathlib.Path(original_path[:-3]).with_suffix('.csv'))
    of = get_csv_output_path(rf)

    pc.set_description('Exporting to ' + of)
    vdf.to_csv(of, float_format='%g')
    pc.update()

    pc.set_description('Exported ' + of)
    pc.update()
    pc.close()


def run():
    with tqdm(desc='Counter line search and counter name parsing regex patterns',
              total=2, leave=False) as pc:
        counter_line_pattern = get_pfx_counter_line_pattern()
        pc.update()
        counter_form_pattern = get_general_counter_form_pattern()
        pc.update()

    def check_regex_patterns_integrity():
        test_general_counter_form_pattern(counter_form_pattern)
        test_pfx_counter_line_pattern(counter_line_pattern)
    with tqdm(desc='Checking regex patterns integrity', leave=False) as pc:
        check_regex_patterns_integrity()

    def list_txt_files_in_cur_dir():
        hpx_output_files = glob.glob('*.txt.xz')
        assert isinstance(hpx_output_files, list)
        assert len(hpx_output_files) >= 1
        return hpx_output_files
    with tqdm(desc='Listing *.txt.xz files in current directory', leave=False) as pc:
        hpx_output_files = list_txt_files_in_cur_dir()

    def task_process_file(rf):
        with tqdm(desc=rf, total=8, leave=True) as pc:
            process_file(rf, counter_line_pattern, counter_form_pattern, pc)

    subject_count = len(hpx_output_files)
    with tqdm(desc='Convert HPX output file(s) to CSV', total=subject_count,
              position=0) as pc:
        with concurrent.futures.ThreadPoolExecutor(4) as executor:
            conversion_tasks = {
                executor.submit(task_process_file, rf):
                    rf for rf in hpx_output_files
            }
            for future in concurrent.futures.as_completed(conversion_tasks):
                rf = conversion_tasks[future]
                try:
                    future.result()
                    pc.update()
                except Exception as ex:
                    print(rf, 'generated an exception:', ex)

        pc.set_description('Conversion finished.')


def main():
    run()


if __name__ == '__main__':
    main()
