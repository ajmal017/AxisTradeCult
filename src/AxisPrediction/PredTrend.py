import Program.GlobalVar as gv
from CommonDef.DefStr import *
from Program.Common import *
from Program.ProcessData import *
from builtins import int
from numpy import NaN
from Statistics_TechIndicators.CalcStatistics import *

from sklearn import datasets
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.neighbors import *
from sklearn.svm import *
from sklearn.naive_bayes import *
from sklearn.neural_network import *
from sklearn.tree import *
from sklearn.gaussian_process import *
from sklearn import metrics
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import label_binarize
from imblearn.over_sampling import RandomOverSampler
from attr._make import validate

def PredTrendA(param):
    # CrashA param
    neighbor_size = 5
    pred_days = 5
    change_rate = 5
    validateDataSize = 3
    
    print("Process Data...")
    df = TransToAdjOHLCbyAdjC(GetStockPriceVolumeData("DIS", gv.StockDataPoolPath, "2000-1-3", "2018-6-01", True))
    
    df = AddNeighborFeatures(df, neighbor_size, DropNan = False)
    
    df = AddMAIndictor(df, window=5, DropNan = False)
    df = AddBollingerBandsIndictor(df, window=5, DropNan = False)
    df = AddKDJIndictor(df, window=5, DropNan = False)

    df = AddMAIndictor(df, window=10, DropNan = False)
    df = AddBollingerBandsIndictor(df, window=10, DropNan = False)
    df = AddKDJIndictor(df, window=10, DropNan = False)
    
    df = AddMAIndictor(df, window=15, DropNan = False)
    df = AddBollingerBandsIndictor(df, window=15, DropNan = False)
    df = AddKDJIndictor(df, window=15, DropNan = False)
    
    df = df.dropna()
    
    #print(df)
    
    RollingVal = pandas.Series.rolling(df[strClose], window = pred_days, center = False).mean()

    ChangeN = pandas.Series(numpy.zeros(shape=(df[strClose].count()),dtype=int), index=df.index)
    ChangeN.rename('Change'+str(change_rate)+'%', inplace=True)

    tmp_index = 0
    for i,v in ChangeN.items():
        pred_index = tmp_index+pred_days
        if pred_index < ChangeN.count():   
            change = (RollingVal.iloc[pred_index] - df[strClose][i]) / df[strClose][i] *100
            if change < -1*change_rate:
                ChangeN[i] = -1
            elif change > change_rate:
                ChangeN[i] = 1
            else:
                ChangeN[i] = 0
                
        else:
            ChangeN[i] = ChangeN.iloc[tmp_index-1]
        
        tmp_index+=1
        
    print(df)     
    print(ChangeN)
    
    print('DataSize: {0}'.format(len(ChangeN)))
    
    print("Process Data finished.")
    
    OutputData = pandas.concat([ df, ChangeN], axis=1)
    OutputData.to_csv("D:\\PredTrendA_data.csv", sep=',');
    
    print("split Tr, Ts Data...")
    ValidateDataList = []
    
    TempData = df.copy()
    TempTarget = ChangeN.copy();
    SplitSize = int(len(df.index) / validateDataSize)
    print('SplitSize: {0}, Total Size: {1}'.format(SplitSize, len(df.index)))
    for i in range(validateDataSize-1):
        data_t = TempData[:SplitSize]
        target_t = TempTarget[:SplitSize]
        ValidateDataList.append({strData: data_t, strTarget: target_t})
        TempData = TempData[SplitSize:]
        TempTarget = TempTarget[SplitSize:]
    
    
    ValidateDataList.append({strData: TempData, strTarget: TempTarget})    
    
    """
    x_train, x_test, y_train, y_test = train_test_split(df, IsChangeN, test_size=0.5)
    ValidateDataList.append({strData: x_train, strTarget: y_train}) 
    ValidateDataList.append({strData: x_test, strTarget: y_test}) 
    """
    
    #print(ValidateDataList)
    
    print("split Tr, Ts over.")
    
    print("Training & Testing Model...")
    
    ValidateResult = []
    for index in range(len(ValidateDataList)-1):
        print("Training & Testing Model{0}...".format(index))
        
        x_train = ValidateDataList[index][strData]
        y_train = ValidateDataList[index][strTarget]       
        x_test = ValidateDataList[index+1][strData]
        y_test = ValidateDataList[index+1][strTarget]
                
        scaler = preprocessing.StandardScaler().fit(x_train)               
        x_train = scaler.transform(x_train)
        x_test = scaler.transform(x_test)    
        
        # Binarize the output
        y_train = label_binarize(y_train, classes=[-1, 0, 1])
        y_test = label_binarize(y_test, classes=[-1, 0, 1])
        
        clf= OneVsRestClassifier(KNeighborsClassifier(n_neighbors=5))
        #clf = LinearSVC(random_state=0) 
        #clf = OneVsRestClassifier(GaussianNB())
        #clf = OneVsRestClassifier(MLPClassifier(solver='lbfgs', alpha=1e-5, hidden_layer_sizes=(5, 2), random_state=1))
        #clf = OneVsRestClassifier(DecisionTreeClassifier(random_state=0))
        #clf = OneVsRestClassifier(GaussianProcessClassifier(kernel=1.0 * kernels.RBF(length_scale=1.0)))
        clf.fit(x_train, y_train) 
        predict_prob = clf.predict_proba(x_test)
        
        # OvR clf.predict may produce [0 0 0] when prob equal: [0.4 0.4 0.2], we calculate by predict_proba
        class_labels = [-1, 0, 1]
        max_prob_index_list = predict_prob.argmax(axis=1)
        temp = []
        for index in range(len(max_prob_index_list)):
            temp.append(class_labels[max_prob_index_list[index]])
        predict_result = label_binarize(temp, class_labels)
        
        ValidateResult.append({strPredictVal: predict_result, strAnsVal: y_test, strPredictProbVal: predict_prob})        
        
        print("Training & Testing Model{0} finished".format(index))
    
    print("Training & Testing finished.")
    
    #print(ValidateResult)
    
    total_result = {strPredictVal:ValidateResult[0][strPredictVal], strPredictProbVal:ValidateResult[0][strPredictProbVal], strAnsVal:ValidateResult[0][strAnsVal]}
    for index in range(1, len(ValidateResult)):
        total_result[strPredictVal] = numpy.concatenate((total_result[strPredictVal], ValidateResult[index][strPredictVal]), axis=0)
        total_result[strPredictProbVal] = numpy.concatenate((total_result[strPredictProbVal], ValidateResult[index][strPredictProbVal]), axis=0)
        total_result[strAnsVal] = numpy.concatenate((total_result[strAnsVal], ValidateResult[index][strAnsVal]), axis=0)
    
    #print(total_result)
    
    ShowSensitivitySpecificityForMultiLabels(total_result[strAnsVal], total_result[strPredictVal], total_result[strPredictProbVal], [1, 0, -1])
    
 
PredTrendFuncDict = {
  strPredTrendA:   {strFuncName: PredTrendA, strParam:{}},
}