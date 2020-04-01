#!/usr/bin/env python3

import concurrent.futures
import os
import traceback

from tqdm import tqdm

from . import helpers, process


def run():
    with tqdm(desc='Listing *.txt.xz files in current directory', leave=False) as pc:
        hpx_output_files = helpers.list_txt_files_in_cur_dir('*.txt.xz')

    def task_process_file(rf):
        with tqdm(desc=rf, total=11, leave=True) as pc:
            r0f = os.path.join(os.curdir, rf)
            with helpers.progress_block('Reading', pc):
                hpx_out = helpers.read_file(r0f)

            vdf = process.process_file(hpx_out, pc)

            of = helpers.get_csv_output_path(rf)

            with helpers.progress_block('Exporting to ' + of, pc):
                vdf.to_csv(of, float_format='%g')

            with helpers.progress_block('Exported ' + of, pc):
                pc.update()
            pc.close()

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
                    print(rf, 'Generated exception:', ex, traceback.format_exc())

        pc.set_description('Conversion finished.')


def main():
    run()
