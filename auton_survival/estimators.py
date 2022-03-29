# coding=utf-8
# MIT License

# Copyright (c) 2022 Carnegie Mellon University, Auton Lab

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Utilities to train survival regression models and estimate survival."""

import numpy as np
import pandas as pd


def _get_valid_idx(n, size, random_seed):

  """Randomly select sample indices to split into train and test data.

  Parameters:
  -----------
  n : int
      Size of the dataset to stratify.
  size : float
      Percentage of n samples to randomly draw.
  random_seed : int
      Controls the reproducibility of randomized indices.

  Return:
  -----------
  np.array : A numpy array of randomly assigned boolean values.

  """

  np.random.seed(random_seed)


  validx = sorted(np.random.choice(n, size=(int(size*n)), replace=False))
  vidx = np.zeros(n).astype('bool')
  vidx[validx] = True

  return vidx

def _fit_dcm(features, outcomes, random_seed, **hyperparams):

  r"""Fit the Deep Cox Mixtures (DCM) [1] model to a given dataset.

   DCM is an extension to the Cox model, modeling an individual's survival
   function using a finite mixture of K Cox models, with the assignment of
   an individual i to each latent group mediated by a gating function.

  References
  -----------
  [1] Nagpal, C., Yadlowsky, S., Rostamzadeh, N., and Heller, K. (2021c).
  Deep cox mixtures for survival regression. In Machine Learning for
  Healthcare Conference, pages 674-708. PMLR

  Parameters
  -----------
  features : pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples
      and columns as covariates.
  outcomes : pd.DataFrame
      A pandas dataframe with columns 'time' and 'event'.
  random_seed : int
      Controls the rproduecibility of fitted estimators.
  hyperparams : dict
      Optional kwarg arguments.
      Keys correspond to parameter names as strings and items correspond
      to parameter values.
      Options include:
      - 'k' : int, default=3
          Size of the underlying Cox mixtures.
      - 'layers' : list, default=[100]
          A list consisting of the number of neurons in each hidden layer.
      - 'batch_size' : int, default=128
          Learning is performed on mini-batches of input data. This parameter
          specifies the size of each mini-batch.
      - 'lr' : float, default=1e-3
          Learning rate for the 'Adam' optimizer.
      - 'epochs' : int, default=50
          Number of complete passes through the training data.
      -'smoothing_factor' : float, default=1e-4

  Returns
  -----------
  Trained instance of the Deep Cox Mixtures model.
  
  """

  from .models.dcm import DeepCoxMixtures

  k = hyperparams.get("k", 3) 
  layers = hyperparams.get("layers", [100])
  batch_size = hyperparams.get("batch_size", 128)
  learning_rate = hyperparams.get("learning_rate", 1e-3)
  epochs = hyperparams.get("epochs", 50)
  smoothing_factor = hyperparams.get("smoothing_factor", 1e-4)
  gamma = hyperparams.get("gamma", 10)

  model = DeepCoxMixtures(k=k,
                          layers=layers,
                          gamma=gamma,
                          smoothing_factor=smoothing_factor)
  
  model.fit(features.values, outcomes.time.values, outcomes.event.values,
            iters=epochs, batch_size=batch_size, learning_rate=learning_rate,
            random_seed=random_seed)
  
  return model

  # if len(layers): model = DeepCoxMixture(k=k, inputdim=features.shape[1], hidden=layers[0])
  # else: model = CoxMixture(k=k, inputdim=features.shape[1])

  # x = torch.from_numpy(features.values.astype('float32'))
  # t = torch.from_numpy(outcomes['time'].values.astype('float32'))
  # e = torch.from_numpy(outcomes['event'].values.astype('float32'))

  # vidx = _get_valid_idx(x.shape[0], 0.15, random_seed)

  # train_data = (x[~vidx], t[~vidx], e[~vidx])
  # val_data = (x[vidx], t[vidx], e[vidx])

  # (model, breslow_splines, unique_times) = train(model,
  #                                                train_data,
  #                                                val_data, 
  #                                                epochs=epochs,
  #                                                lr=lr, bs=bs,
  #                                                use_posteriors=True,
  #                                                patience=5,
  #                                                return_losses=False,
  #                                                smoothing_factor=smoothing_factor)

  #return (model, breslow_splines, unique_times)

def _predict_dcm(model, features, times):

  """Predict survival probabilities at specified time(s) using the
  Deep Cox Mixtures model.

  Parameters
  -----------
  model : Trained instance of the Deep Cox Mixtures model.
  features : pd.DataFrame
      A pandas dataframe with rows corresponding to individual
      samples and columns as covariates.
  times: float or list
      A float or list of the times at which to compute
      the survival probability.

  Returns
  -----------
  np.array : A numpy array of the survival probabilites at each time point in times.

  """

  #raise NotImplementedError()

  survival_predictions = model.predict_survival(features, times)
  if len(times)>1:
    survival_predictions = pd.DataFrame(survival_predictions, columns=times).T
    return __interpolate_missing_times(survival_predictions, times)
  else:
    return survival_predictions

def _fit_dcph(features, outcomes, random_seed, **hyperparams):

  """Fit a Deep Cox Proportional Hazards Model/Farragi Simon Network [1,2]
   model to a given dataset.

  References
  -----------
  [1] Faraggi, David, and Richard Simon. "A neural network model for survival
  data." Statistics in medicine 14.1 (1995): 73-82.
  [2] Katzman, Jared L., et al. "DeepSurv: personalized treatment recommender
  system using a Cox proportional hazards deep neural network."
  BMC medical research methodology 18.1 (2018): 1-12.

  Parameters:
  -----------
  features : pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples
      and columns as covariates.
  outcomes : pd.DataFrame
      A pandas dataframe with columns 'time' and 'event'.
  random_seed : int
      Controls the reproducibility of called functions.
  hyperparams : dict
      Optional arguments for the estimator stored in a python dictionary.
      Keys correspond to parameter names as strings and items correspond
      to parameter values.
      Options include:
      - 'layers' : list, default=[100]
          A list consisting of the number of neurons in each hidden layer.
      - 'lr' : float, default=1e-3
          Learning rate for the 'Adam' optimizer.
      - 'bs' : int, default=100
          Learning is performed on mini-batches of input data.
          This parameter specifies the size of each mini-batch.
      - 'epochs' : int, default=50
          Number of complete passes through the training data.
      - 'activation' : str, default='relu'
          Activation function
          Options include: 'relu', 'relu6', 'tanh'
 
  Return:
  -----------
  Trained instance of the Deep Cox Proportional Hazards model.

  """
  raise NotImplementedError()
  # import torch
  # import torchtuples as ttup

  # from pycox.models import CoxPH

  # torch.manual_seed(random_seed)
  # np.random.seed(random_seed)

  # layers = hyperparams.get('layers', [100])
  # lr = hyperparams.get('lr', 1e-3)
  # bs = hyperparams.get('bs', 100)
  # epochs = hyperparams.get('epochs', 50)
  # activation = hyperparams.get('activation', 'relu')

  # if activation == 'relu': activation = torch.nn.ReLU
  # elif activation == 'relu6': activation = torch.nn.ReLU6
  # elif activation == 'tanh': activation = torch.nn.Tanh
  # else: raise NotImplementedError("Activation function not implemented")

  # x = features.values.astype('float32')
  # t = outcomes['time'].values.astype('float32')
  # e = outcomes['event'].values.astype('bool')

  # in_features = x.shape[1]
  # out_features = 1
  # batch_norm = False
  # dropout = 0.0

  # net = ttup.practical.MLPVanilla(in_features, layers,
  #                                 out_features, batch_norm, dropout,
  #                                 activation=activation,
  #                                 output_bias=False)

  # model = CoxPH(net, torch.optim.Adam)

  # vidx = _get_valid_idx(x.shape[0], 0.15, random_seed)

  # y_train, y_val = (t[~vidx], e[~vidx]), (t[vidx], e[vidx])
  # val_data = x[vidx], y_val

  # callbacks = [ttup.callbacks.EarlyStopping()]
  # model.fit(x[~vidx], y_train, bs, epochs, callbacks, True,
  #           val_data=val_data,
  #           val_batch_size=bs)
  # model.compute_baseline_hazards()

  return model

def __interpolate_missing_times(survival_predictions, times):
  """Interpolate survival probabilities at missing time points.

  Parameters
  -----------
  survival_predictions : pd.DataFrame
      A pandas dataframe of the survival probabilites at each time
      in times.
  times: float or list
      A float or list of the times at which to compute the
      survival probability.

  Returns
  -----------
  pd.DataFrame : Survival probabilities interpolated using 'backfill'
  method at missing time points.

  """

  nans = np.full(survival_predictions.shape[1], np.nan)
  not_in_index = list(set(times) - set(survival_predictions.index))

  for idx in not_in_index:
    survival_predictions.loc[idx] = nans
  return survival_predictions.sort_index(axis=0).interpolate().interpolate(method='bfill').T[times].values

def _predict_dcph(model, features, times):
  """Predict survival at specified time(s) using the Deep Cox PH model.

  Parameters
  -----------
  model:
      Trained instance of the Deep Cox PH model.
  features: pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples and
      columns as covariates.
  times: float or list
      A float or list of the times at which to compute the survival probability.

  Returns
  -----------
  pd.DataFrame : A pandas dataframe of the survival probabilites at each
  time point in times.

  """
  if isinstance(times, float) or isinstance(times, int):
    times = [float(times)]

  survival_predictions = model.predict_surv_df(features.values.astype('float32'))

  return __interpolate_missing_times(survival_predictions, times)


def _fit_cph(features, outcomes, random_seed, **hyperparams):
  """Fit a linear Cox Proportional Hazards model to a given dataset.

  Parameters
  -----------
  features : pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples and
      columns as covariates.
  outcomes : pd.DataFrame
      A pandas dataframe with columns 'time' and 'event'.
  random_seed : int
      Controls the reproducibility of called functions.
  hyperparams : dict
      Optional arguments for the estimator stored in a python dictionary.
      Keys correspond to parameter names as strings and items correspond 
      to parameter values.
      Options include:
      - 'lr' : float, default=1e-3
          Learning rate

  Returns
  -----------
  Trained instance of the Cox Proportional Hazards model.

  """

  from lifelines import CoxPHFitter

  data = outcomes.join(features)
  penalizer = hyperparams.get('l2', 1e-3)

  return CoxPHFitter(penalizer=penalizer).fit(data, 
                                              duration_col='time', 
                                              event_col='event')

def _fit_rsf(features, outcomes, random_seed, **hyperparams):

  """Fit the Random Survival Forests (RSF) [1] model to a given dataset.
  RSF is an extension of Random Forests to the survival settings where
  risk scores are computed by creating Nelson-Aalen estimators in the
  splits induced by the Random Forest.

  References
  -----------
  [1] Hemant Ishwaran et al. Random survival forests.
  The annals of applied statistics, 2(3):841–860, 2008.

  Parameters
  -----------
  features : pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples and columns
      as covariates.
  outcomes : pd.DataFrame
      A pandas dataframe with columns 'time' and 'event'.
  random_seed : int
      Controls the reproducibility of called functions.
  hyperparams : dict
      Optional arguments for the estimator stored in a python dictionary.
      Keys correspond to parameter names as strings and items correspond
      to parameter values.
      Options include:
      - 'n_estimators' : int, default=50
          Number of trees.
      - 'max_depth' : int, default=5
          Maximum depth of the tree.
      - 'max_features' : str, default='sqrt'
          Number of features to consider when looking for the best split.

  Returns
  -----------
  Trained instance of the Random Survival Forests model.

  """

  from sksurv.ensemble import RandomSurvivalForest
  from sksurv.util import Surv

  n_estimators = hyperparams.get("n_estimators", 50)
  max_depth = hyperparams.get("max_depth", 5)
  max_features = hyperparams.get("max_features", 'sqrt')

  # Initialize an RSF model. 
  rsf = RandomSurvivalForest(n_estimators=n_estimators,
                             max_depth=max_depth,
                             max_features=max_features,
                             random_state=random_seed,
                             n_jobs=-1)

  y =  Surv.from_dataframe('event', 'time', outcomes)
  # Fit the RSF model
  rsf.fit(features.values, y)
  return rsf


def _fit_dsm(features, outcomes, random_seed, **hyperparams):

  """Fit the Deep Survival Machines (DSM) [1] model to a given dataset.

  DSM is a fully parametric approach and improves on the Accelerated
  Failure Time model by modelling the event time distribution as a
  fixed size mixture over Weibull or Log-Normal distributions.

  References
  -----------
  [1] Nagpal, Chirag, Xinyu Li, and Artur Dubrawski.
  "Deep survival machines: Fully parametric survival regression
  and representation learning for censored data with competing risks."
  IEEE Journal of Biomedical and Health Informatics 25.8 (2021): 3163-3175.

  Parameters
  -----------
  features : pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples and
      columns as covariates.
  outcomes : pd.DataFrame
      A pandas dataframe with columns 'time' and 'event'.
  random_seed : int
      Controls the reproducibility of called functions.
  hyperparams : dict
      Optional arguments for the estimator stored in a python dictionary.
      Keys correspond to parameter names as strings and items correspond
      to parameter values.
      Options include:
      - 'layers' : list
          A list of integers describing the dimensionality of each hidden layer.
      - 'iters' : int, default=10
          The maximum number of training iterations on the training dataset.
      - 'distribution' : str, default='Weibull'
          Choice of the underlying survival distributions.
          Options include: 'Weibull' and 'LogNormal'.
      - 'temperature' : float, default=1.0
          The value with which to rescale the logits for the gate.

  Returns
  -----------
  Trained instance of the Deep Survival Machines model.

  """

  from .models.dsm import DeepSurvivalMachines

  k = hyperparams.get("k", 3)
  layers = hyperparams.get("layers", [100])
  iters = hyperparams.get("iters", 10)
  distribution = hyperparams.get("distribution", "Weibull")
  temperature = hyperparams.get("temperature", 1.0)

  model = DeepSurvivalMachines(k=k, layers=layers,
                               distribution=distribution,
                               temp=temperature)

  model.fit(features.values,
            outcomes['time'].values,
            outcomes['event'].values,
            iters=iters)

  return model

def _predict_dsm(model, features, times):

  """Predict survival at specified time(s) using the Deep Survival Machines.

  Parameters
  -----------
  model : Trained instance of the Deep Suvival Machines model.
  features : pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples and
      columns as covariates.
  times: float or list
      A float or list of the times at which to compute survival probability.

  Returns
  -----------
  np.array : numpy array of the survival probabilites at each point in times.

  """

  return model.predict_survival(features.values, times)

def _predict_cph(model, features, times):

  """Predict survival probabilities at specified time(s) using a
  linear Cox Proportional Hazards.

  Parameters
  -----------
  model : Trained instance of the Cox Proportional Hazards model.
  features : pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples
      and columns as covariates.
  times: float or list
      A float or list of the times at which to compute the survival probability.

  Returns
  -----------
  np.array : numpy array of the survival probabilites at each time point in times.

  """

  if isinstance(times, float): times = [times] 
  return model.predict_survival_function(features, times=times).values.T

def _predict_rsf(model, features, times):

  """Predict survival probabilities at specified time(s) using a
  Random Survival Forest.

  Parameters
  -----------
  model:
      Trained instance of the Random Survival Forests model.
  features: pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples and columns as covariates.
  times: float or list
      A float or list of the times at which to compute the survival probability.

  Returns
  -----------
  pd.DataFrame : A pandas dataframe of the survival probabilites at each time point in times.
      Probabilities are interpolated using 'backfill' method at missing time points.
  
  """

  if isinstance(times, float) or isinstance(times, int):
    times = [float(times)]

  survival_predictions = model.predict_survival_function(features.values, return_array=True)
  survival_predictions = pd.DataFrame(survival_predictions, columns=model.event_times_).T

  return __interpolate_missing_times(survival_predictions, times)

def _predict_dcm(model, features, times):

  """Predict survival at specified time(s) using Deep Cox Mixtures.

  Parameters
  -----------
  model:
      Trained instance of the Deep Cox Mixtures model.
  features: pd.DataFrame
      A pandas dataframe with rows corresponding to individual samples
      and columns as covariates.
  times: float or list
      A float or list of the times at which to compute the survival
      probability.

  Returns
  -----------
  pd.DataFrame : A pandas dataframe of the survival probabilites at each
  time point in times.

  """

  if isinstance(times, float) or isinstance(times, int):
    times = [float(times)]

  from .models.dcm.dcm_utilities import predict_scores

  import torch
  x = torch.from_numpy(features.values.astype('float32'))

  survival_predictions = predict_scores(model, x, times)
  survival_predictions = pd.DataFrame(survival_predictions, columns=times).T

  return __interpolate_missing_times(survival_predictions, times)

class SurvivalModel:

  """Universal interface to train multiple different survival models.

  Parameters
  -----------
  model : str
      A string that determines the choice of the surival analysis model.
      Survival model choices include:

      - 'dsm' : Deep Survival Machines [3] model
      - 'dcph' : Deep Cox Proportional Hazards [2] model
      - 'dcm' : Deep Cox Mixtures [4] model
      - 'rsf' : Random Survival Forests [1] model
      - 'cph' : Cox Proportional Hazards [2] model

  random_seed: int
      Controls the reproducibility of called functions.


  References
  -----------

  [1] Hemant Ishwaran et al. Random survival forests.
  The annals of applied statistics, 2(3):841–860, 2008.

  [2] Cox, D. R. (1972). Regression models and life-tables.
  Journal of the Royal Statistical Society: Series B (Methodological).

  [3] Chirag Nagpal, Xinyu Li, and Artur Dubrawski.
  Deep survival machines: Fully parametric survival regression and
  representation learning for censored data with competing risks. 2020.

  [4] Nagpal, C., Yadlowsky, S., Rostamzadeh, N., and Heller, K. (2021c).
  Deep cox mixtures for survival regression.
  In Machine Learning for Healthcare Conference, pages 674–708. PMLR

  """

  _VALID_MODELS = ['rsf', 'cph', 'dsm', 'dcph', 'dcm']

  def __init__(self, model, random_seed=0, **hyperparams):

    assert model in SurvivalModel._VALID_MODELS

    self.model = model
    self.hyperparams = hyperparams
    self.random_seed = random_seed
    self.fitted = False

  def fit(self, features, outcomes,
          weights=None, resample_size=1.0, weights_clip=1e-2):

    """This method is used to train an instance of the survival model.

    Parameters
    -----------
    features: pd.DataFrame
        a pandas dataframe with rows corresponding to individual samples and
        columns as covariates.
    outcomes : pd.DataFrame
        a pandas dataframe with columns 'time' and 'event'.
    weights: list or np.array
        a list or numpy array of importance weights for each sample.
    resample_size: float
        a float between 0 and 1 that controls the size of the resampled dataset.
    weights_clip: float
        a float that controls the minimum and maximum importance weight.
        (To reduce estimator variance.)

    Returns
    --------
    self
        Trained instance of a survival model.

    """

    if weights is not None:
      assert len(weights) == features.shape[0], "Size of passed weights must match size of training data."
      assert ((weights>0.0)&(weights<=1.0)).all(), "Weights must be in the range (0,1]."

      weights[weights>(1-weights_clip)] = 1-weights_clip
      weights[weights<(weights_clip)] = weights_clip

      data = features.join(outcomes)
      data_resampled = data.sample(weights = weights, 
                                   frac = resample_size,
                                   replace = True,
                                   random_state = self.random_seed)
      features = data_resampled[features.columns]
      outcomes = data_resampled[outcomes.columns]


    if self.model == 'cph': self._model = _fit_cph(features, outcomes, self.random_seed, **self.hyperparams)
    elif self.model == 'rsf': self._model = _fit_rsf(features, outcomes, self.random_seed, **self.hyperparams)
    elif self.model == 'dsm': self._model = _fit_dsm(features, outcomes, self.random_seed, **self.hyperparams)
    elif self.model == 'dcph': self._model = _fit_dcph(features, outcomes, self.random_seed, **self.hyperparams)
    elif self.model == 'dcm': self._model = _fit_dcm(features, outcomes, self.random_seed, **self.hyperparams)
    else : raise NotImplementedError()

    self.fitted = True
    return self

  def predict_survival(self, features, times):

    """Predict survival probabilities at specified time(s).

    Parameters
    -----------
    features: pd.DataFrame
        a pandas dataframe with rows corresponding to individual samples
        and columns as covariates.
    times: float or list
        a float or list of the times at which to compute the survival probability.

    """

    if self.model == 'cph': return _predict_cph(self._model, features, times)
    elif self.model == 'rsf': return _predict_rsf(self._model, features, times)
    elif self.model == 'dsm': return _predict_dsm(self._model, features, times)
    elif self.model == 'dcph': return _predict_dcph(self._model, features, times)
    elif self.model == 'dcm': return _predict_dcm(self._model, features, times)
    else : raise NotImplementedError()

  def predict_risk(self, features, times):

    """Predict risk of an outcome occurring within the specified time(s).

    Parameters
    -----------
    features : pd.DataFrame
        a pandas dataframe with rows corresponding to individual samples and
        columns as covariates.
    times: float or list
        a float or list of the times at which to compute the risk.

    Returns
    ---------
    np.array
        numpy array of the outcome risks at each time point in times.

    """

    return 1 - self.predict_survival(features, times)

class CounterfactualSurvivalModel:

  """Universal interface to train multiple different counterfactual 
     survival models."""

  def __init__(self, treated_model, control_model):

    assert isinstance(treated_model, SurvivalModel)
    assert isinstance(control_model, SurvivalModel)
    assert treated_model.fitted
    assert control_model.fitted

    self.treated_model = treated_model
    self.control_model = control_model

  def predict_counterfactual_survival(self, features, times):

    control_outcomes = self.control_model.predict_survival(features, times)
    treated_outcomes = self.treated_model.predict_survival(features, times)

    return treated_outcomes, control_outcomes

  def predict_counterfactual_risk(self, features, times):

    control_outcomes = self.control_model.predict_risk(features, times)
    treated_outcomes = self.treated_model.predict_risk(features, times)

    return treated_outcomes, control_outcomes