#!/usr/bin/env python3

import concurrent.futures
import os

from tqdm import tqdm

from . import helpers, patterns, process


def run():
    with tqdm(desc='Counter line search and counter name parsing regex patterns',
              total=2, leave=False) as pc:
        counter_line_pattern = patterns.get_pfx_counter_line_pattern()
        pc.update()
        counter_form_pattern = patterns.get_general_counter_form_pattern()
        pc.update()

    with tqdm(desc='Listing *.txt.xz files in current directory', leave=False) as pc:
        hpx_output_files = helpers.list_txt_files_in_cur_dir('*.txt.xz')

    def task_process_file(rf):
        with tqdm(desc=rf, total=8, leave=True) as pc:
            r0f = os.path.join(os.curdir, rf)
            pc.set_description('Reading')
            hpx_out = helpers.read_file(r0f)
            pc.update()

            vdf = process.process_file(
                hpx_out, counter_line_pattern, counter_form_pattern, pc)

            of = helpers.get_csv_output_path(rf)

            pc.set_description('Exporting to ' + of)
            vdf.to_csv(of, float_format='%g')
            pc.update()

            pc.set_description('Exported ' + of)
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
                    print(rf, 'Generated exception:', ex)

        pc.set_description('Conversion finished.')


def main():
    run()
