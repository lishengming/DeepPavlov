# Copyright 2017 Neural Networks and Deep Learning lab, MIPT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import json
import xlsxwriter
import matplotlib.pyplot as plt

from typing import List
from collections import OrderedDict
from os.path import join, isdir
from os import mkdir


# --------------------------------------------------- Common ----------------------------------------------------------

def normal_time(z):
    if z > 1:
        h = z/3600
        m = z % 3600/60
        s = z % 3600 % 60
        t = '%i:%i:%i' % (h, m, s)
    else:
        t = '{0:.2}'.format(z)
    return t


def merge_logs(old_log, new_log):
    """ Combines two logs into one """
    # update time
    t_old = old_log['experiment_info']['full_time'].split(':')
    t_new = new_log['experiment_info']['full_time'].split(':')
    sec = int(t_old[2]) + int(t_new[2]) + (int(t_old[1]) + int(t_new[1])) * 60 + (
            int(t_old[0]) + int(t_new[0])) * 3600
    old_log['experiment_info']['full_time'] = normal_time(sec)
    # update num of pipes
    n_old = int(old_log['experiment_info']['number_of_pipes'])
    n_new = int(new_log['experiment_info']['number_of_pipes'])
    old_log['experiment_info']['number_of_pipes'] = n_old + n_new

    new_datasets = []
    new_models = {}
    for dataset_name, dataset_val in new_log['experiments'].items():
        if dataset_name not in old_log['experiments'].keys():
            new_datasets.append(dataset_name)
        else:
            new_models[dataset_name] = []
            for name, val in dataset_val.items():
                if name not in old_log['experiments'][dataset_name].keys():
                    new_models[dataset_name].append(name)

    for dataset_name, dataset_val in new_log['experiments'].items():
        if dataset_name not in new_datasets:
            for name, val in dataset_val.items():
                if name not in new_models[dataset_name]:
                    for nkey, nval in new_log['experiments'][dataset_name][name].items():
                        match = False
                        for okey, oval in old_log['experiments'][dataset_name][name].items():
                            if nval['config'] == oval['config']:
                                match = True
                        if not match:
                            n_old += 1
                            old_log['experiments'][dataset_name][name][str(n_old)] = nval

    for dataset_name in new_models.keys():
        if len(new_models[dataset_name]) != 0:
            for model_name in new_models[dataset_name]:
                old_log['experiments'][dataset_name][model_name] = OrderedDict()
                for nkey, nval in new_log['experiments'][dataset_name][model_name].items():
                    n_old += 1
                    old_log['experiments'][dataset_name][model_name][str(n_old)] = nval

    for dataset_name in new_datasets:
        for model_name, model_val in new_log['experiments'][dataset_name].items():
            for nkey, nval in new_log['experiments'][dataset_name][model_name].items():
                n_old += 1
                old_log['experiments'][dataset_name][model_name][str(n_old)] = nval

    return old_log


# ------------------------------------------------Generate reports-----------------------------------------------------

# ________________________________________________Generate new table___________________________________________________
def get_data(log):
    dataset_names = {}
    max_com = 0

    for dataset_name, models_val in log['experiments'].items():
        dataset_names[dataset_name] = []
        pipelines = []
        for model_name, val in models_val.items():
            for num, conf in val.items():
                pipe = dict(index=int(num), components=[], res={})
                # max amount of components
                if max_com < len(conf['config']):
                    max_com = len(conf['config'])

                for component in conf['config']:
                    comp_data = dict()
                    comp_data['name'] = component.pop('component_name')

                    if 'save_path' in component.keys():
                        del component['save_path']
                    if 'load_path' in component.keys():
                        del component['load_path']
                    if 'scratch_init' in component.keys():
                        del component['scratch_init']
                    if 'name' in component.keys():
                        del component['name']
                    if 'id' in component.keys():
                        del component['id']
                    if 'in' in component.keys():
                        del component['in']
                    if 'in_y' in component.keys():
                        del component['in_y']
                    if 'out' in component.keys():
                        del component['out']
                    if 'main' in component.keys():
                        del component['main']
                    if 'out' in component.keys():
                        del component['out']
                    if 'fit_on' in component.keys():
                        del component['fit_on']

                    comp_data['conf'] = component
                    pipe['components'].append(comp_data)

                for name, val_ in conf['results'].items():
                    pipe['res'][name] = val_
                pipelines.append(pipe)
        dataset_names[dataset_name].append(pipelines)

    return max_com, dataset_names


def write_info(sheet, num, target_metric, cell_format):
    # Start from the first cell. Rows and columns are zero indexed.
    # write info
    sheet.write(0, 0, "Number of pipelines:", cell_format)
    sheet.write(0, 1, num, cell_format)
    sheet.write(0, 2, "Target metric:", cell_format)
    sheet.write(0, 3, target_metric, cell_format)
    return 2, 0


def write_legend(sheet, row, col, data_tipe, metric_names, max_com, cell_format):
    # write legend
    sheet.write(row, col, "Pipeline", cell_format)
    sheet.merge_range(row, col + 1, row, max_com - 1, "Preprocessing", cell_format)
    sheet.write(row, max_com, "Model", cell_format)
    for j in range(len(data_tipe)):
        p = j*len(metric_names)
        for k, met in enumerate(metric_names):
            sheet.write(row, max_com + p + k + 1, met, cell_format)

    return row + 1, col


def write_dataset_name(sheet, sheet_2, row_1, row_2, col, name, dataset_list, format_, max_l, target_metric,
                       metric_names):
    # write dataset name
    sheet.write(row_1, col, "Dataset name", format_)
    sheet.write(row_1, col + 1, name, format_)
    for l, type_d in enumerate(dataset_list[0][0]['res'].keys()):
        p = l*len(metric_names)
        sheet.merge_range(row_1, max_l + p + 1, row_1, max_l + p + len(metric_names), type_d, format_)
    row_1 += 1

    # write dataset name
    sheet_2.write(row_2, col, "Dataset name", format_)
    sheet_2.write(row_2, col + 1, name, format_)
    for l, type_d in enumerate(dataset_list[0][0]['res'].keys()):
        p = l * len(metric_names)
        sheet_2.merge_range(row_2, max_l + p + 1, row_2, max_l + p + len(metric_names), type_d, format_)
    row_2 += 1

    row_1, row_2 = write_batch_size(row_1, row_2, col, dataset_list, sheet, sheet_2, format_, max_l, target_metric,
                                    metric_names)

    return row_1, row_2


def write_batch_size(row1, row2, col, model_list, sheet, sheet_2, _format, max_l, target_metric, metric_names):
    row_1 = row1
    row_2 = row2

    for val_ in model_list:
        row_1, col = write_legend(sheet, row_1, col, list(val_[0]['res'].keys()), metric_names, max_l, _format)
        row_2, col = write_legend(sheet_2, row_2, col, list(val_[0]['res'].keys()), metric_names, max_l, _format)

        # Write pipelines table
        row_1 = write_table(sheet, val_, row_1, col, _format, max_l)
        # Get the best pipelines
        best_pipelines = get_best(val_, target_metric)
        # Sorting pipelines
        best_pipelines = sort_pipes(best_pipelines, target_metric)
        # Write sort pipelines table
        row_2 = write_table(sheet_2, best_pipelines, row_2, col, _format, max_l, write_conf=False)

        row_1 += 2
        row_2 += 2

    return row_1, row_2


def write_metrics(sheet, comp_dict, start_x, start_y, cell_format):
    data_names = list(comp_dict['res'].keys())
    metric_names = list(comp_dict['res'][data_names[-1]].keys())

    for j, tp in enumerate(data_names):
        p = j*len(comp_dict['res'][tp])
        for k, met in enumerate(metric_names):
            sheet.write(start_x, start_y + p + k + 1, comp_dict['res'][tp][met], cell_format)
    return None


def write_config(sheet, comp_dict, x, y, cell_format):
    z = {}
    for i, comp in enumerate(comp_dict['components']):
        z[str(i)] = comp['conf']
    s = json.dumps(z)
    sheet.write(x, y, s, cell_format)
    return None


def write_pipe(sheet, pipe_dict, start_x, start_y, cell_format, max_, write_conf):
    """ Add pipeline to the table """
    data_names = list(pipe_dict['res'].keys())
    metric_names = list(pipe_dict['res'][data_names[-1]].keys())

    sheet.write(start_x, start_y, pipe_dict['index'], cell_format)
    x = start_x
    y = start_y + 1
    if len(pipe_dict['components']) > 2:
        for conf in pipe_dict['components'][:-2]:
            sheet.write(x, y, conf['name'], cell_format)
            y += 1
    if len(pipe_dict['components'][:-1]) < max_ - 1:
        sheet.merge_range(x, y, x, max_ - 1, pipe_dict['components'][-2]['name'], cell_format)
    else:
        sheet.write(x, y, pipe_dict['components'][-2]['name'], cell_format)
    sheet.write(x, max_, pipe_dict['components'][-1]['name'], cell_format)
    write_metrics(sheet, pipe_dict, x, max_, cell_format)
    if write_conf:
        write_config(sheet, pipe_dict, x, max_ + len(data_names)*len(metric_names) + 1, cell_format)
    return None


def write_table(worksheet, pipelines, row, col, cell_format, max_l, write_conf=True):
    # Write pipelines table
    for pipe in pipelines:
        write_pipe(worksheet, pipe, row, col, cell_format, max_l, write_conf)
        row += 1
    return row


def get_best(data, target):
    def get_name(pipeline):
        z = []
        for com in pipeline['components']:
            z.append(com['name'])
        return '->'.join(z)

    best_pipes = []
    inds = []
    buf = dict()
    for pipe in data:
        pipe_name = get_name(pipe)
        if pipe_name not in buf.keys():
            tp = list(pipe['res'].keys())[-1]
            buf[pipe_name] = {'ind': pipe['index'], 'target': pipe['res'][tp][target]}
        else:
            tp = list(pipe['res'].keys())[-1]
            if buf[pipe_name]['target'] <= pipe['res'][tp][target]:
                buf[pipe_name]['target'] = pipe['res'][tp][target]
                buf[pipe_name]['ind'] = pipe['index']

    for key, val in buf.items():
        inds.append(val['ind'])

    del buf

    for pipe in data:
        if pipe['index'] in inds:
            best_pipes.append(pipe)

    return best_pipes


def sort_pipes(pipes, target_metric):
    ind_val = []
    sort_pipes_ = []
    dtype = [('value', 'float'), ('index', 'int')]
    for pipe in pipes:
        if 'test' not in pipe['res'].keys():
            name = list(pipe['res'].keys())[0]
        else:
            name = 'test'
        rm = pipe['res'][name]
        ind_val.append((rm[target_metric], pipe['index']))

    ind_val = np.sort(np.array(ind_val, dtype=dtype), order='value')
    for com in ind_val:
        ind = com[1]
        for pipe in pipes:
            if pipe['index'] == ind:
                sort_pipes_.append(pipe)

    del pipes, ind_val

    sort_pipes_.reverse()

    return sort_pipes_


def build_pipeline_table(log_data, target_metric=None, save_path='./'):
    exp_name = log_data['experiment_info']['exp_name']
    date = log_data['experiment_info']['date']
    metrics = log_data['experiment_info']['metrics']
    num_p = log_data['experiment_info']['number_of_pipes']
    if target_metric is None:
        target_metric = metrics[0]

    # read data from log
    max_l, pipe_data = get_data(log_data)
    # create xlsx table form
    workbook = xlsxwriter.Workbook(join(save_path, 'Report_{0}_{1}.xlsx'.format(exp_name, date)))
    worksheet_1 = workbook.add_worksheet("Pipelines_sort")
    worksheet_2 = workbook.add_worksheet("Pipelines_table")
    # Create a cell format
    cell_format = workbook.add_format({'bold': 1,
                                       'border': 1,
                                       'align': 'center',
                                       'valign': 'vcenter'})
    # write legend to tables
    row, col = write_info(worksheet_1, num_p, target_metric, cell_format)
    row, col = write_info(worksheet_2, num_p, target_metric, cell_format)

    row1 = row
    row2 = row

    for dataset_name, dataset_dict in pipe_data.items():
        row1, row2 = write_dataset_name(worksheet_2, worksheet_1, row1, row2, col, dataset_name, dataset_dict,
                                        cell_format, max_l, target_metric, metrics)

    workbook.close()
    return None


# ___________________________________________________Generate plots___________________________________________________


def get_met_info(log_):

    def analize(log, metrics_: List[str]):
        main = dict()

        for name in list(log.keys()):
            print(name)
            main[name] = dict()
            for met in metrics_:
                met_max = -np.inf
                for key, val in log[name].items():
                    if val['results'].get('test') is not None:
                        if val['results']['test'][met] > met_max:
                            met_max = val['results']['test'][met]
                    else:
                        print("Warning pipe with number {} not contain 'test' key in results, and it will not "
                              "participate in comparing the results to display the final plot.")
                main[name][met] = met_max
        return main

    data = {}
    metrics = log_['experiment_info']['metrics']
    for dataset_name, models_val in log_['experiments'].items():
        data[dataset_name] = analize(models_val, metrics)
    return data


def plot_res(info, name, savepath='./', save=True, width=0.2, fheight=8, fwidth=12, ext='png'):
    # prepeare data

    bar_list = []
    models = list(info.keys())
    metrics = list(info[models[0]].keys())
    n = len(metrics)

    for met in metrics:
        tmp = []
        for model in models:
            tmp.append(info[model][met])
        bar_list.append(tmp)

    x = np.arange(len(models))

    # ploting
    fig, ax = plt.subplots()
    fig.set_figheight(fheight)
    fig.set_figwidth(fwidth)

    colors = plt.cm.Paired(np.linspace(0, 0.5, len(bar_list)))
    # add some text for labels, title and axes ticks
    ax.set_ylabel('Scores').set_fontsize(20)
    ax.set_title('Scores by metric').set_fontsize(20)

    bars = []
    for i, y in enumerate(bar_list):
        if i == 0:
            bars.append(ax.bar(x, y, width, color=colors[i]))
        else:
            bars.append(ax.bar(x + i*width, y, width, color=colors[i]))

    # plot x sticks and labels
    ax.set_xticks(x - width / 2 + n * width / 2)
    ax.set_xticklabels(tuple(models), fontsize=15)

    yticks = ax.get_yticks()
    ax.set_yticklabels(['{0:.2}'.format(float(y)) for y in yticks], fontsize=15)

    ax.grid(True, linestyle='--', color='b', alpha=0.1)

    # plot legend
    # ax.legend(tuple([bar[0] for bar in bars]), tuple(metrics), loc='upper left', bbox_to_anchor=(1, 1))
    ax.legend(tuple([bar[0] for bar in bars]), tuple(metrics))

    # auto lables
    def autolabel(columns):
        for rects in columns:
            for rect in rects:
                height = rect.get_height()
                ax.text(rect.get_x() + rect.get_width() / 2., 1.05 * height, '{0:.2}'.format(float(height)),
                        ha='center', va='bottom', fontsize=12)

    autolabel(bars)
    plt.ylim(0, 1.1)

    # show the picture
    if not save:
        plt.show()
    else:
        if not isdir(savepath):
            mkdir(savepath)
        adr = join(savepath, '{0}.{1}'.format(name, ext))
        fig.savefig(adr, dpi=100)
        plt.close(fig)

    return None


# _________________________________________________Built report_______________________________________________________


def results_visualization(root, savepath, plot, target_metric=None):
    with open(join(root, root.split('/')[-1] + '.json'), 'r') as log_file:
        log = json.load(log_file)
        log_file.close()

    # create the xlsx file with results of experiments
    build_pipeline_table(log, target_metric=target_metric, save_path=root)
    # build_report(log, target_metric=target_metric, save_path=root)
    if plot:
        # scrub data from log for image creating
        info = get_met_info(log)
        # plot histograms
        for dataset_name, dataset_val in info.items():
            plot_res(dataset_val, dataset_name, savepath)

    return None
