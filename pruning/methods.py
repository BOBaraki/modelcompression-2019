import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

def get_all_weights(model):
    weights = []

    if len(list(model.children())) != 0:
        for l in model.children():
            weights += get_all_weights(l)
    else:
        for p in model.parameters():
            if len(p.data.size()) != 1: # Avoid bias parameters
                weights += list(p.cpu().data.abs().numpy().flatten())

    return weights

def gen_masks_for_layer(model, threshold):
    # generate mask
    for p in model.parameters():
        if len(p.data.size()) != 1:
            pruned_inds = p.data.abs() > threshold
            return pruned_inds.float()
    
def gen_masks_recursive(model, threshold):
    masks = []
    
    for module in model.children():
        if 'Masked' not in str(type(module)):
            print("Skipping masking of layer: ", module)
            continue
        if len(list(module.children())) != 0:
            masks.append(gen_masks_recursive(module, threshold))
        else:
            masks.append(gen_masks_for_layer(module, threshold))
    
    return masks


def weight_prune(model, pruning_perc):
    '''
    Prune pruning_perc% weights globally (not layer-wise)
    arXiv: 1606.09274
    '''    
    all_weights = get_all_weights(model)
    threshold = np.percentile(np.array(all_weights), pruning_perc)
    return gen_masks_recursive(model, threshold)

def prune_rate(model, verbose=True):
    """
    Print out prune rate for each layer and the whole network
    """
    total_nb_param = 0
    nb_zero_param = 0

    layer_id = 0

    for parameter in model.parameters():

        param_this_layer = 1
        for dim in parameter.data.size():
            param_this_layer *= dim
        total_nb_param += param_this_layer

        # only pruning linear and conv layers
        if len(parameter.data.size()) != 1:
            layer_id += 1
            zero_param_this_layer = \
                np.count_nonzero(parameter.cpu().data.numpy()==0)
            nb_zero_param += zero_param_this_layer

            if verbose:
                print("Layer {} | {} layer | {:.2f}% parameters pruned" \
                    .format(
                        layer_id,
                        'Conv' if len(parameter.data.size()) == 4 \
                            else 'Linear',
                        100.*zero_param_this_layer/param_this_layer,
                        ))
    pruning_perc = 100.*nb_zero_param/total_nb_param
    if verbose:
        print("Final pruning rate: {:.2f}%".format(pruning_perc))
    return pruning_perc