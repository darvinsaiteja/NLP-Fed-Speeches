''' Post Data Pull Workflow

At this point in the program we have pulled and processed both the Fed speeches and interest rate date.
FED SPEECHES
    The results of this process have been saved in a pickle file in the data subdirectory called
        'ts_cosine_sim.p'
        It contains a list with the following three variables [ts_cos_last, ts_cos_avg_n, ts_date]
            ts_cos_last     contains the cosine similarity of the last fed speech to the ones on the ts_date
            ts_cos_avg_n    contains the cos. sim of the last 50 speeches to the ones made on ts_date
            ts_date is      contains the date in a crappy np.datetime64 object

    os.chdir("..")
    pickle_out = open('../data/ts_cosine_sim', 'wb')
    pickle.dump([ts_cos_last, ts_cos_avg_n, ts_dates], pickle_out)
    pickle_out.close()

INTEREST RATE DATA
    The interest rate data has been pulled from quandl and pre-processed. The data sits in a file called 'interest_rate_data.p'


STEPS:
    1. Load up the interest rate data
    2. Split into train/test
    3. Convert into three datasets
        raw yields
        discrete forwards
        cont.comp forwards
    4. EDA on the data in the training + cv set
    5. build model pipeline
        -estimate parameters of the model over the training set
        -build CV update parameters/etc
    6. Compare the results

'''



''' Working on the Gaussian Model for the MVP on base level rates '''
def forecast_gaussian(X):
    ''' Mean zero interest rates we just take the change here '''
    fcst = 0
    return fcst

''' ARIMA MODEL ON BASE RATES
For now lets just look at the 10 year
'''

def build_ARIMA_model(X, ar, ma, diff_ord, target):

    model = pf.ARIMA(data=X, ar=4, ma=4, integ = diff_ord, target=target, family = pf.Normal())

    # Estimate the latent variables with a maximum likelihood estimation
    model.fit("MLE")
    #x.summary()
    pred = model.predict(h=1)
    last_rate = X['10 YR'][-1]
    this_shock = pred['Differenced 10 YR'].iloc[0]
    next_rate = last_rate + this_shock

    return next_rate

def update_cv_data(X_train, X_cv, i):

    temp = X_cv[0:i]
    frames = [X_train, temp]
    X_this_cv = pd.concat(frames)

    return X_this_cv

def create_cv_forecasts(X_train, X_cv, dict_params):
    cv_len = len(X_cv)
    forecasts = np.zeros(shape=[cv_len,1])
    ar = dict_params['ar']
    ma = dict_params['ma']
    diff_ord = dict_params['diff_ord']
    target = dict_params[target]
    for i in range(cv_len):
        print(i)
        this_X = update_cv_data(X_train, X_cv, i)
        forecasts[i] = build_ARIMA_model(this_X, ar, ma, diff_ord,
                            target, family = pf.Normal())
    return forecasts

def cross_validate_models(model_list, X_train, X_cv):
    '''
    Building a overlaying function that handles the cross validation

    Will take as an input model_list that includes the model type
    and all of the hyper parameters of the model

    INPUTS:
        X_train -   the dataframe containing the training dataset
        X_cv -      the dataframe containing the cross_val dataset
        model_list  A dictionary containing the hyper parameters
                     of the model

    OUTPUTS
        The forecast of the model (one day interest rate forecast) will be stored
        in the model_list['foreacst'] section

 'model_type'    {'Gaussian', 'ARIMA', 'ARIMAX'}
    'name'          name given to model for charting purposes
    'target_class'  {'rates', 'forwards', 'cc_forwards'}
    'hyper_parms'    A dictoinary containing the hyperparmeters of the model
    'forecast'      A zero, initially that get populated with the daily forecasts over CV period

    '''
    # setting up the initial arima model
    for idx, item in enumerate(model_list):
        # Making sure we use the correct interest rate transformation

        if item['target_class']=='rates':
            print('This one uses rates')

        elif item['target_class']=='forwards':
            print('This model uses forwards')
        elif item['target_class']=='cc_forwards':
            print("This model uses continuously compounded forwards")

        if item['model_type']== 'ARIMA':
            model_list[i]['forecast'] = create_cv_forecasts(X_train, X_cv, item['hyper_params'])

    return model_list





#Load up interest rate data
import numpy as np
import pandas as pd
import pyflux as pf
import datetime as datetime
import matplotlib.pyplot as plt
import os
import pickle
import ForecastModel as fc

if __name__ == '__main__':

    X_fwds = pickle.load(open('../data/forward_rates', 'rb'))
    #X_fwds = df_add_first_diff(X_fwds)

    #df_FX = pickle.load( open( "data/FX_data", "rb" ) )
    # Loading up the federal reserve speech data
    #fed_metrics = pickle.load( open( "../data/mvp_cosine_sim", "rb" ) )
    fed_metrics = pickle.load( open( "../data/policy_speech_dist", "rb" ) )
    cos_last = fed_metrics['cos_last']
    cos_avg_n = fed_metrics['cos_avg_n']
    ed_last = fed_metrics['ed_last']
    ed_avg_n = fed_metrics['ed_avg_n']
    fed_dates = fed_metrics['dates']

    #grouping by date (some dates had multiple speeches)
    avgstats = pd.DataFrame({'date':fed_dates,
                            'ed_last': ed_last,
                            'ed_avg_n': ed_avg_n,
                            'cos_last': cos_last,
                            'cos_avg_n': cos_avg_n}).groupby('date').mean()
    avgstats.index = pd.to_datetime(avgstats.index)

    X_fwds = X_fwds.merge(avgstats, how='left', left_index = True, right_index = True)
    X_fwds.fillna(value=0, inplace=True)

    # the first row of X_fwds contains zeros for the differenced rates, clear them here
    X_fwds = X_fwds.drop(X_fwds.index[0])

    # Creating training, cross-validation and test datasets
    total_obs = len(X_fwds)
    train_int = int(round(total_obs*.7, 0))
    cv_int = int(round(total_obs*.85, 0))

    fwd_train = X_fwds[0:train_int]
    fwd_cv = X_fwds[train_int:cv_int]
    fwd_test = X_fwds[cv_int:]

    # saving the cross validation data set for reporting and charts later
    pickle_out = open('../data/fwd_cv_data', 'wb')
    pickle.dump(fwd_cv, pickle_out)
    pickle_out.close()

    forecast_matrix = np.zeros(shape=(len(fwd_cv), 7))
    # Base models to be estimated
    model_list= []
    ''' ARIMA model'''
    this_name = 'Normal ARIMA(1,0,1)'
    model_type = pf.ARIMA
    model_class = 'ARIMA'
    model_target= 'd_ten_y'
    model_dep_vars = 'None'
    hyper_params= {'ar':1, 'ma': 1, "diff_ord": 0}
    num_components = 3
    model_inputs = {'model_type': model_type,
                    'model_class': model_class,
                    'name': this_name,
                    'target': model_target,
                    'dep_vars': model_dep_vars,
                    'hyper_params': hyper_params,
                    'num_components': num_components,
                    'forecast': np.copy(forecast_matrix)}
    model_list.append(model_inputs)

    ''' ARMIAX model '''
    this_name = 'Normal ARIMAX(1,0,1)'
    model_type = pf.ARIMAX
    model_class = 'ARIMAX'
    model_target= 'd_ten_y'
    model_dep_vars = 'ed_last'
    hyper_params= {'ar':1, 'ma': 1, "diff_ord": 0}
    num_components = 3
    model_inputs = {'model_type': model_type,
                    'model_class': model_class,
                    'name': this_name,
                    'target': model_target,
                    'dep_vars': model_dep_vars,
                    'hyper_params': hyper_params,
                    'num_components': num_components,
                    'formula':'d_ten_y~1+ed_last',
                    'forecast': np.copy(forecast_matrix)}
    model_list.append(model_inputs)

    ''' Gaussian Model '''
    this_name = 'Gaussian'
    model_class = 'Gaussian'
    model_target= 'd_ten_y'
    model_dep_vars = 'None'
    num_components = 3
    model_inputs = {'model_class': model_class,
                    'name': this_name,
                    'target': model_target,
                    'dep_vars': model_dep_vars,
                    'num_components': num_components,
                    'forecast': np.copy(forecast_matrix)}
    model_list.append(model_inputs)
    '''BELOW ARE THE PCA MODELS'''
    ''' ARIMA model'''
    this_name = 'Normal ARIMA(1,0,1)'
    model_type = pf.ARIMA
    model_class = 'ARIMA'
    model_target= 'PCA'
    model_dep_vars = 'None'
    hyper_params= {'ar':1, 'ma': 1, "diff_ord": 0}
    num_components = 3
    model_inputs = {'model_type': model_type,
                    'model_class': model_class,
                    'name': this_name,
                    'target': model_target,
                    'dep_vars': model_dep_vars,
                    'hyper_params': hyper_params,
                    'num_components': num_components,
                    'forecast': np.copy(forecast_matrix)}
    model_list.append(model_inputs)

    ''' ARMIAX model '''
    this_name = 'Normal ARIMAX(1,0,1)'
    model_type = pf.ARIMAX
    model_class = 'ARIMAX'
    model_target= 'PCA'
    model_dep_vars = 'ed_last'
    hyper_params= {'ar':1, 'ma': 1, "diff_ord": 0}
    num_components = 3
    model_inputs = {'model_type': model_type,
                    'model_class': model_class,
                    'name': this_name,
                    'target': model_target,
                    'dep_vars': model_dep_vars,
                    'hyper_params': hyper_params,
                    'num_components': num_components,
                    'formula':'d_ten_y~1+ed_last',
                    'forecast': np.copy(forecast_matrix)}
    model_list.append(model_inputs)

    ''' Gaussian Model '''
    this_name = 'Gaussian'
    model_class = 'Gaussian'
    model_target= 'PCA'
    model_dep_vars = 'None'
    num_components = 3
    model_inputs = {'model_class': model_class,
                    'name': this_name,
                    'target': model_target,
                    'dep_vars': model_dep_vars,
                    'num_components': num_components,
                    'forecast': np.copy(forecast_matrix)}
    model_list.append(model_inputs)




    ''' Adding PCA versions of the models above'''
    # for model in model_list:
    #     this_model = model.copy()
    #     this_model['model_target']='PCA'
    #     model_list.append(this_model)

    # create the list of column names to go over
    col_names = ['d_six_m', 'd_one_y', 'd_two_y', 'd_three_y', 'd_five_y', 'd_seven_y', 'd_ten_y']

    # now that we have the basic models, we need to run these models for every forward rate and
    # for all of the dates in the cv dataset

    #for i in col_names:

    for this_rate in range(len(col_names)):
        print("Running model for ", col_names[this_rate])

        # adjust the models to reflect this particular forward
        ''' possibly change this to be a function of the model itself '''
        for model in model_list:
            # The PCA based models use the entire term structure. For the models that
            # estimate each spot rate seperatelly, we need to reassign the target variables
            if model['target'] != 'PCA':
                # the arimax model needs to have the 'patsy' function adjusted
                if model['model_class'] == 'ARIMAX':
                    model['target'] = col_names[this_rate]
                    func_str = model['formula']
                    func_list = func_str.split(sep='~')
                    model['formula'] = col_names[this_rate] + '~' + func_list[1]
                    # NOTE: May need to adjust if I am using levels here!

                else:
                    model['target']= col_names[this_rate] # ARIMAX model

        #initialize the models
        base_models = []
        for model in model_list:
            base_models.append(fc.ForecastModel(model))

        # start the loop for the dates
        #for d in range(len(fwd_cv)):
        for day_index in range(len(fwd_cv)):
        #for day_index in range(10):
            # basic print statment to know where we are in the process
            if day_index % 2 == 0:
                print('We are on day : ', day_index)
            # updating the time series by one day
            X = update_cv_data(fwd_train, fwd_cv, day_index)

            for model_index, m in enumerate(model_list):
                # need an if statement here to have PCA based models only fit once
                if m['target'] == 'PCA':
                    # only fit if on the first interest rate
                    print("This is the current pca model", m)
                    print("this is the this_rate variable", this_rate)
                    if this_rate == 0:
                        this_model = base_models[model_index]
                        this_model.fit(X)
                        print("here is some numbers ")
                        this_prediction = this_model.predict_one(X)
                        #if type(this_prediction)== np.float64:
                            #model_list[model_index]['forecast'][day_index,:]= this_prediction
                        model_list[model_index]['forecast'][day_index,:]= this_prediction
                        # else:
                        #     print(" here is the type of the prediction", type(this_prediction))
                        #     print('this prediction', this_prediction)
                        #     model_list[model_index]['forecast'][day_index,:] = this_prediction

                # below is the case where we are NOT fitting a PCA model
                else:
                    this_model = base_models[model_index]
                    this_model.fit(X)
                    this_prediction = this_model.predict_one(X)
                    model_list[model_index]['forecast'][day_index,this_rate] = this_prediction
                    #if type(this_prediction)== np.float64:
                    #    model_list[model_index]['forecast'][day_index,this_rate]= this_prediction
                    #else:
                    #    model_list[model_index]['forecast'][day_index,this_rate] = this_prediction.iloc[0,0]


    ''' Here I need to create the loop that takes care of the PCA type models
    These are different because we do not loop over every individual rate but use them all
        -pca and mean levels (Gaussian Version)
        -PCA with ARIMA
        -PCA with ARIMAX
            -base speeches
            -level of interest rates
        -need the loop above to only fit the PCA classes once
    THAT IS ALL I NEED TO DO

    '''
    #import ForecastModel as fc
    # to relaod the foreacst model first load the following module
    # from importlib import reload
    # The type reload(fc)
    # reload(fc)
    # below saves the output from these three models to a pickle file
    pickle_out = open('../data/May_3_model_results', 'wb')
    pickle.dump(model_list, pickle_out)
    pickle_out.close()

    X = fwd_cv[['d_six_m', 'd_one_y', 'd_two_y', 'd_three_y', 'd_five_y', 'd_seven_y', 'd_ten_y']].values

    delta_list = []

    dist_0 = X - model_list[0]['forecast']
    dist_1 = X - model_list[1]['forecast']
    dist_2 = X - model_list[2]['forecast']
    dist_3 = X - model_list[3]['forecast']
    dist_4 = X - model_list[4]['forecast']
    dist_5 = X - model_list[5]['forecast']

    delta_list = [dist_0, dist_1, dist_2, dist_3, dist_4, dist_5]

    #pickle_out = open('../data/Tuesday_distrib', 'wb')
    pickle_out = open('../data/May_3_distrib', 'wb')
    pickle.dump(delta_list, pickle_out)
    pickle_out.close()
