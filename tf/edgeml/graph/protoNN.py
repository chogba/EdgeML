# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT license.

import numpy as np
import tensorflow as tf


class ProtoNN:
    def __init__(self, inputDimension, projectionDimension, numPrototypes,
                 numOutputLabels, gamma,
                 W = None, B = None, Z = None):
        '''
        inputDimension: input data dimension. A [-1, inputDimension] matrix
            is expected as part of __call__ method.
        projectionDimension: (model paramter)
        numPrototypes: (model parameter)
        numOutputLabels: The number of output labels or classes
        W, B, Z: initial value to use for W, B, Z
        Expected Dimensions:
        W   d x d_cap
        B   d_cap x m
        Z   L x m
        X   n x d
        '''
        with tf.name_scope('protoNN') as ns:
            self.__nscope = ns
        self.__d = inputDimension
        self.__d_cap = projectionDimension
        self.__m = numPrototypes
        self.__L = numOutputLabels

        self.__inW = W
        self.__inB = B
        self.__inZ = Z
        self.__inGamma = gamma
        # The tf.Variables
        self.W, self.B, self.Z = None, None, None
        self.gamma = None

        self.__validInit = False
        self.__initWBZ()
        self.__initGamma()
        self.__validateInit()
        self.protoNNOut = None
        self.predictions = None
        self.accuracy = None

    def __validateInit(self):
        self.__validInit = False
        errmsg = "Dimensions mismatch! Should be W[d, d_cap]"
        errmsg += ", B[d_cap, m] and Z[L, m]"
        d, d_cap, m, L, _ = self.getHyperParams()
        assert self.W.shape[0] == d, errmsg
        assert self.W.shape[1] == d_cap, errmsg
        assert self.B.shape[0] == d_cap, errmsg
        assert self.B.shape[1] == m, errmsg
        assert self.Z.shape[0] == L, errmsg
        assert self.Z.shape[1] == m, errmsg
        self.__validInit = True

    def __initWBZ(self):
        with tf.name_scope(self.__nscope):
            W = self.__inW
            if W is None:
                W = tf.random_normal_initializer()
                W = W([self.__d, self.__d_cap])
            self.W = tf.Variable(W, name='W', dtype=tf.float32)

            B = self.__inB
            if B is None:
                B = tf.random_uniform_initializer()
                B = B([self.__d_cap, self.__m])
            self.B = tf.Variable(B, name='B', dtype=tf.float32)

            Z = self.__inZ
            if Z is None:
                Z = tf.random_normal_initializer()
                Z = Z([self.__L, self.__m])
            Z = tf.Variable(Z, name='Z', dtype=tf.float32)
            self.Z = Z
        return self.W, self.B, self.Z

    def __initGamma(self):
        with tf.name_scope(self.__nscope):
            gamma = self.__inGamma
            self.gamma = tf.constant(gamma, name='gamma')

    def getHyperParams(self):
        d = self.__d
        dcap = self.__d_cap
        m = self.__m
        L = self.__L
        return d, dcap, m, L, self.gamma

    def getModelMatrices(self):
        return self.W, self.B, self.Z, self.gamma

    def __call__(self, X, Y=None):
        '''
        Returns a protoNN graph
        Returned y is of dimension [-1, numLabels]

        X is [-1, d]
        Y is [-1, numLabels] . Y is optional; if provided will be used
            to create an accuracy computation operator.
        '''
        # This should never execute
        assert self.__validInit is True, "Initialization failed!"
        if self.protoNNOut is not None:
            return self.protoNNOut

        W, B, Z, gamma = self.W, self.B, self.Z, self.gamma
        with tf.name_scope(self.__nscope):
            WX = tf.matmul(X, W)
            # Convert WX to tensor so that broadcasting can work
            dim = [-1, WX.shape.as_list()[1], 1]
            WX = tf.reshape(WX, dim)
            dim = [1, B.shape.as_list()[0], -1]
            B = tf.reshape(B, dim)
            l2sim = B - WX
            l2sim = tf.pow(l2sim, 2)
            l2sim = tf.reduce_sum(l2sim, 1, keepdims=True)
            self.l2sim = l2sim
            gammal2sim = (-1 * gamma * gamma) * l2sim
            M = tf.exp(gammal2sim)
            dim = [1] + Z.shape.as_list()
            Z = tf.reshape(Z, dim)
            y = tf.multiply(Z, M)
            y = tf.reduce_sum(y, 2, name='protoNNScoreOut')
            self.protoNNOut = y
            self.predictions = tf.argmax(y, 1, name='protoNNPredictions')
            if Y is not None:
                target = tf.argmax(Y, 1)
                correctPrediction = tf.equal(self.predictions, target)
                acc = tf.reduce_mean(tf.cast(correctPrediction, tf.float32),
                                     name='protoNNAccuracy')
                self.accuracy = acc
        return y

    def getPredictionsOp(self):
        return self.predictions

    def getAccuracyOp(self):
        msg = "Accuracy operator not defined in graph. Did you provide Y as an"
        msg += " argument to _call_?"
        assert self.accuracy is not None, msg
        return self.accuracy
