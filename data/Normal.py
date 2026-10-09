# -*- coding: utf-8 -*-
"""
Code for the estimation of the Normal distribution parameters

This code requires the distribution values to be provided in a single column on a txt file

@author: Juan Pablo Torres

Scroll to end of code for user input required parameters
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

def statistics(distribution,variablename,variableunits):
    
    distribution = np.sort(distribution) # Sort array ascending 
    std = stats.nanstd(distribution) # Computes standard deviation
    mu = stats.nanmean(distribution) # Computes mean value
    cv = std/mu * 100 # computes coefficient of variation
    cvstr = '%.2f' % (cv) # float to string conversion
    mustr  = '%.2f' % (mu) # float to string conversion
    stdstr  = '%.2f' % (std) # float to string conversion
    fontsize = 22

    plt.hist(distribution,bins=8,normed=True,color='orange',edgecolor='white',linewidth=5)
    plt.xlabel(variablename + '(' + variableunits + ')',fontname='Times New Roman',fontsize=fontsize)
    plt.ylabel('Probability density',fontname='Times New Roman',fontsize=fontsize)
       
   # Normal distribution plot

    x = np.arange(((min(distribution)-2*std)*100),((2*std+max(distribution))*100))/100 # range of values to plot the distribution
    plt.plot(x, 1/(std * np.sqrt(2 * np.pi)) * np.exp( - (x - mu)**2 / (2 * std**2) ),linewidth=4, color='brown')
    titulo = ('Mean = ' + mustr + variableunits + ', Standard Deviation = ' + stdstr + variableunits + ',' + 'CV = ' + cvstr + ' %')
    plt.title(titulo,fontsize=16,fontname='Times New Roman')
       
    
#################################################################################################################################################
# USER INPUT PARAMETERS #########################################################################################################################
#################################################################################################################################################   

# Enter filename (file should contain a column with the discrete values of the distribution to be analized, e.g. Flax-0_S.txt')
    # Remember to include the full path to file if file is not in the python script working directory
filename = 'Carbon-0_E.txt'
# Enter variable name (e.g. 'Strength')
varname  = 'Strength'
# Enter units (e.g. 'MPa')
unit = 'MPa'

# Program loads the file and calculates Weibull parameters, which are displayed in the pop-up figure
dist = np.loadtxt(filename)  
statistics(dist,varname,unit)      