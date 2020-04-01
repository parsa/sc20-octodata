import contextlib
import glob
import lzma
import os
import pathlib


def read_file(filepath):
    assert os.access(filepath, os.R_OK)

    with lzma.open(filepath, 'rt', encoding='utf-8') as hpx_output_handle:
        hpx_output = hpx_output_handle.read()
    return hpx_output


def list_txt_files_in_cur_dir(pattern):
    hpx_output_files = glob.glob(pattern)
    assert isinstance(hpx_output_files, list)
    assert len(hpx_output_files) >= 1
    return hpx_output_files


def get_csv_output_path(original_path):
    return str(pathlib.Path(original_path[:-3]).with_suffix('.csv'))


@contextlib.contextmanager
def progress_block(msg, pc):
    try:
        pc.set_description(msg)
        yield
    finally:
        pc.update()
