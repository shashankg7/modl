import time
from math import sqrt

import matplotlib.pyplot as plt
import numpy as np
from numpy.random import RandomState
from sklearn.datasets import fetch_olivetti_faces
from sklearn.externals.joblib import Parallel
from sklearn.externals.joblib import delayed

from modl.dict_fact import DictMF


def sqnorm(X):
    return sqrt(np.sum(X ** 2))


class Callback(object):
    """Utility class for plotting RMSE"""

    def __init__(self, X_tr):
        self.X_tr = X_tr
        self.obj = []
        self.rmse = []
        self.rmse_tr = []
        self.times = []
        self.sparsity = []
        self.iter = []
        self.q = []
        self.start_time = time.clock()
        self.test_time = 0

    def __call__(self, mf):
        test_time = time.clock()
        P = mf.transform(self.X_tr)
        loss = np.sum((self.X_tr - P.T.dot(mf.components_)) ** 2)
        regul = mf.alpha * np.sum(P ** 2)
        self.obj.append(loss + regul)

        self.q.append(mf.Q_[1, np.linspace(0, 4095, 20, dtype='int')].copy())
        self.sparsity.append(np.sum(mf.Q_ != 0) / mf.Q_.size)
        self.test_time += time.clock() - test_time
        self.times.append(time.clock() - self.start_time - self.test_time)
        self.iter.append(mf.n_iter_)


def plot_gallery(title, images, n_col, n_row, image_shape):
    plt.figure(figsize=(2. * n_col, 2.26 * n_row))
    plt.suptitle(title, size=16)
    for i, comp in enumerate(images):
        plt.subplot(n_row, n_col, i + 1)
        vmax = max(comp.max(), -comp.min())
        plt.imshow(comp.reshape(image_shape), cmap=plt.cm.gray,
                   interpolation='nearest',
                   vmin=-vmax, vmax=vmax)
        plt.xticks(())
        plt.yticks(())
    plt.subplots_adjust(0.01, 0.05, 0.99, 0.93, 0.04, 0.)


def main():
    n_row, n_col = 3, 6
    n_components = n_row * n_col
    image_shape = (64, 64)
    rng = RandomState(0)

    ###############################################################################
    # Load faces data
    dataset = fetch_olivetti_faces(shuffle=True, random_state=rng)
    faces = dataset.data

    n_samples, n_features = faces.shape

    # global centering
    faces_centered = faces - faces.mean(axis=0)

    # local centering
    faces_centered -= faces_centered.mean(axis=1).reshape(n_samples, -1)
    faces_centered /= np.sqrt(np.sum(faces_centered ** 2, axis=1))[:, np.newaxis]

    print("Dataset consists of %d faces" % n_samples)
    data = faces_centered

    res = Parallel(n_jobs=2)(
        delayed(single_run)(n_components, impute, full_projection, data)
        for impute in [True, False]
        for full_projection in [True, False])

    fig, axes = plt.subplots(3, 1, sharex=True)
    fig.subplots_adjust(left=0.15, right=0.7)
    for cb, estimator in res:
        axes[0].plot(cb.iter, cb.obj,
                     label='impute : %s\n full proj % s' % (estimator.impute, estimator.full_projection))
        axes[1].plot(cb.iter, cb.sparsity,
                     label='impute : %s\n  full proj % s' % (estimator.impute, estimator.full_projection))
        axes[2].plot(cb.iter, np.array(cb.q)[:, 2],
                     label='impute : %s\n  full proj % s' % (estimator.impute, estimator.full_projection))

    axes[0].legend(loc='upper left', bbox_to_anchor=(1, 1))
    axes[0].set_ylabel('Function value')
    axes[1].set_ylabel('Dictionary value')

    axes[2].set_xlabel('# iter')
    # axes[2].legend()
    axes[2].set_ylabel('Dictionary value')
    plt.show()


def single_run(n_components, impute, full_projection, data):
    cb = Callback(data)
    estimator = DictMF(n_components=n_components, batch_size=10,
                       reduction=3, l1_ratio=1, alpha=0.1, max_n_iter=100000,
                       full_projection=full_projection,
                       persist_P=True,
                       impute=impute,
                       backend='c',
                       verbose=3,
                       learning_rate=0.75,
                       offset=1000,
                       random_state=0,
                       callback=cb)
    estimator.fit(data)
    return cb, estimator


if __name__ == '__main__':
    main()
