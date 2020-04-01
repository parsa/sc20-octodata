import numpy as np
import pandas as pd

from .helpers import progress_block
from .patterns import generator_reader


def check_and_prune_fields(df):
    def drop_irrelevant_counters(df):
        def drop_values(column, value):
            df.drop(df.index[df[column] == value], inplace=True)
        # Drop AGAS results
        drop_values('objectname', 'agas')
        # Drop threads...pool#default/worker-thread...count/cumulative-phases
        drop_values('countername', 'count/cumulative-phases')
        drop_values('countername', 'count/cumulative')

    # Units can only be [0.01%], 1, [s], and [ns]
    def check_all_data_units(df):
        for i in df.value_unit.unique():
            assert i in ['[s]', '[ns]', '[0.01%]'] or np.isnan(i)

    def remove_unused_columns(df):
        del df['timestamp_unit']
        del df['value_unit']
        del df['timestamp']

    assert isinstance(df, pd.DataFrame)

    drop_irrelevant_counters(df)
    check_all_data_units(df)
    remove_unused_columns(df)


def process_df(df):
    def get_octotiger_counters(df):
        octo_pivot = df.pivot_table(
            index=['iteration', 'locality'],
            columns=['countername'],
            values='value',
            dropna=False)
        del octo_pivot['idle-rate']
        return octo_pivot
    octotiger_counters = get_octotiger_counters(df)

    def get_idle_rate_counters(df):
        idle_rate_pivot = df.pivot_table(
            index=['iteration', 'locality'],
            columns=['thread_id'],
            values='value')
        return idle_rate_pivot
    idle_rates = get_idle_rate_counters(df)

    result = pd.concat([octotiger_counters, idle_rates], axis=1)
    return result


def process_file(hpx_out, pc):
    with progress_block('Extracting counters', pc):
        df = pd.read_csv(
            generator_reader(hpx_out),
            names=['full_counter_name', 'iteration', 'timestamp',
                   'timestamp_unit', 'value', 'value_unit'],
            dtype={'full_counter_name': 'str', 'iteration': 'uint64',
                   'timestamp': 'float64', 'timestamp_unit': 'str',
                   'value': 'float64', 'value_unit': 'str'},
        )

    assert 0 != len(df)

    assert 0 == len(df[df.iteration.isna()])
    assert 0 == len(df[df.timestamp.isna()])
    assert 0 == len(df[df.timestamp_unit.isna()])
    assert 0 == len(df[df.value.isna()])

    with progress_block('Parsing counter names', pc):
        df[['objectname', 'locality', 'instancename', 'countername']] = \
            df.full_counter_name.str.extract(
                r'/(.+){locality#(\d+)/(.+)}/(.+)', expand=True)

    assert 0 == len(df[df.objectname.isna()])
    assert 0 == len(df[df.locality.isna()])
    assert 0 == len(df[df.instancename.isna()])
    assert 0 == len(df[df.countername.isna()])

    assert 0 != len(df[df.objectname == 'octotiger'])

    with progress_block('Parsing worker thread ids', pc):
        df['thread_id'] = df.instancename.str.extract(
            r'pool#default/worker-thread#(\d+)',
            expand=True).astype('uint64', errors='ignore')

    df.locality = df.locality.astype('uint64', errors='raise')

    with progress_block('Fixing units', pc):
        df.iteration = pd.to_numeric(df.iteration, downcast='unsigned')
        df.timestamp = pd.to_numeric(df.timestamp)
        df.value = pd.to_numeric(df.value)
        df.thread_id = pd.to_numeric(df.thread_id, downcast='unsigned')

    with progress_block('Convert nanoseconds to seconds', pc):
        df.loc[df.value_unit == '[0.01%]', 'value'] *= 0.01
        df.loc[df.value_unit == '[ns]', 'value'] *= 1.0e-9
        df.loc[df.value_unit == '[ns]', 'value_unit'] = '[s]'

    with progress_block('Pruning fields', pc):
        check_and_prune_fields(df)

    with progress_block('Extracting values', pc):
        vdf = process_df(df)

    return vdf
