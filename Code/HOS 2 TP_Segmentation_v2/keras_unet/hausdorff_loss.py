import tensorflow as tf
import numpy as np
import math
from sklearn.utils.extmath import cartesian

def tf_repeat(tensor, repeats):
    """
    Args:

    input: A Tensor. 1-D or higher.
    repeats: A list. Number of repeat for each dimension, length must be the same as the number of dimensions in input

    Returns:

    A Tensor. Has the same type as input. Has the shape of tensor.shape * repeats
    """
    with tf.compat.v1.variable_scope("repeat"):
        expanded_tensor = tf.expand_dims(tensor, -1)
        multiples = [1] + repeats
        tiled_tensor = tf.tile(expanded_tensor, multiples=multiples)
        repeated_tensor = tf.reshape(tiled_tensor, tf.shape(tensor) * repeats)
    return repeated_tensor


def Weighted_Hausdorff_loss(y_true, y_pred, img_size=256, batch_size=16):
    # https://arxiv.org/pdf/1806.07564.pdf
    # y_true: [batch, h, w, 1]
    # y_pred: [batch, h, w, 1]
    resized_height, resized_width = (img_size, img_size)
    max_dist = math.sqrt(resized_height ** 2 + resized_width ** 2)
    n_pixels = resized_height * resized_width
    all_img_locations = tf.convert_to_tensor(cartesian([np.arange(resized_height), np.arange(resized_width)]),
                                             tf.float32)
    terms_1 = []
    terms_2 = []
    # y_true = tf.squeeze(y_true, -1)
    y_pred = tf.squeeze(y_pred, -1)
    # y_pred = tf.squeeze(y_pred, axis=-1)
    #     y_true = tf.reduce_mean(y_true, axis=-1)
    #     y_pred = tf.reduce_mean(y_pred, axis=-1)
    for b in range(batch_size):
        gt_b = y_true[b]
        prob_map_b = y_pred[b]
        # Pairwise distances between all possible locations and the GTed locations
        n_gt_pts = tf.reduce_sum(gt_b)
        gt_b = tf.where(tf.cast(gt_b, tf.bool))
        gt_b = tf.cast(gt_b, tf.float32)
        d_matrix = tf.sqrt(tf.maximum(tf.reshape(tf.reduce_sum(gt_b * gt_b, axis=1), (-1, 1)) + tf.reduce_sum(
            all_img_locations * all_img_locations, axis=1) - 2 * (tf.matmul(gt_b, tf.transpose(all_img_locations))),
                                      0.0))
        d_matrix = tf.transpose(d_matrix)
        # Reshape probability map as a long column vector,
        # and prepare it for multiplication
        p = tf.reshape(prob_map_b, (n_pixels, 1))
        n_est_pts = tf.reduce_sum(p)
        p_replicated = tf_repeat(tf.reshape(p, (-1, 1)), [1, n_gt_pts])
        eps = 1e-6
        alpha = 4
        # Weighted Hausdorff Distance
        term_1 = (1 / (n_est_pts + eps)) * tf.reduce_sum(p * tf.reshape(tf.reduce_min(d_matrix, axis=1), (-1, 1)))
        d_div_p = tf.reduce_min((d_matrix + eps) / (p_replicated ** alpha + eps / max_dist), axis=0)
        d_div_p = tf.clip_by_value(d_div_p, 0, max_dist)
        term_2 = tf.reduce_mean(d_div_p, axis=0)
        terms_1.append(term_1)
        terms_2.append(term_2)
    terms_1 = tf.stack(terms_1)
    terms_2 = tf.stack(terms_2)
    terms_1 = tf.reduce_mean(terms_1)
    # print('term1: '+str(term_1.numpy()))
    terms_2 = tf.reduce_mean(terms_2)
    # print('term2: '+str(term_2.numpy()))
    res = terms_1 + terms_2
    return res

def Huber_loss(batch_size, y_true, y_pred, delta=1):
    smoothL1loss = []
    for b in range(batch_size):
        smoothL1loss.append(tf.keras.losses.huber(y_true=y_true[b],
                                                  y_pred=y_pred[b],
                                                  delta=delta))
    smoothL1loss = tf.stack(smoothL1loss)
    smoothL1loss = tf.reduce_mean(smoothL1loss)
    return smoothL1loss