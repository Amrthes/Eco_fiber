# -*- coding: utf-8 -*-
"""
Code for the estimation of Weibull parameters using rank regression (http://reliawiki.com/index.php/The_Weibull_Distribution)

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
    mustr  = '%.2f' % (mu) # float to string conversion
    stdstr  = '%.2f' % (std) # float to string conversion
    fontsize = 22

    plt.hist(distribution,bins=8,normed=True,color='orange',edgecolor='white',linewidth=5)
    plt.xlabel(variablename + '(' + variableunits + ')',fontname='Times New Roman',fontsize=fontsize)
    plt.ylabel('Probability density',fontname='Times New Roman',fontsize=fontsize)
       
    N = len(distribution)        
    conta = 1        
    mr = []
   # Calculate median rank positions  
    for element in distribution:
        mrval = (conta-0.3)/(N+0.4)
        mr = np.append(mr,mrval)
        conta += 1
   # Calculate rank regression
    y = np.log(-np.log(1-mr))
    x = np.log(distribution)
    xy = np.multiply(x,y)
   # calculate ahat and bhat 
    bhat = (np.sum(xy)-((np.sum(x)*np.sum(y))/N))/(np.sum(np.power(x,2))-((np.sum(x)**2))/N)
    ahat = (np.sum(y)/N) - (bhat*(np.sum(x)/N))
   # Calculate Weibull modulus and scaling parameter 
    beta = bhat
    eta = np.exp(-ahat/bhat)
            # create names
    betastr  = '%.2f' % (beta) # float to string conversion
    etastr  = '%.2f' % (eta) # float to string conversion
   # Plot Weibull PDF  
   # Prepare parameter display in figure title    
    titulo = ( variablename + ': Mean = ' + mustr + variableunits + ', Standard Deviation = ' + stdstr + variableunits + '\n' +
                    'Weibull Modulus = ' +  betastr + ', Scaling Parameter = ' + etastr )         
    plt.title(titulo,fontsize=18,fontname='Times New Roman')
    # Weibull plot
    x = np.arange(((min(distribution)-2*std)*100),((2*std+max(distribution))*100))/100 # range of values to plot the distribution
    plt.plot(x,weibull(x,beta,eta),'r',linewidth=5,color='brown') 

       
# Weibul PDF function        
def weibull(x,beta,eta):
    return (beta/eta) * (x/eta)**(beta-1) * np.exp(-(x/eta)**beta)
    
#################################################################################################################################################
# USER INPUT PARAMETERS #########################################################################################################################
#################################################################################################################################################   

# Enter filename (file should contain a column with the discrete values of the distribution to be analized, e.g. Flax-0_S.txt')
    # Remember to include the full path to file if file is not in the python script working directory
filename = 'Flax-0_S.txt'
# Enter variable name (e.g. 'Strength')
varname  = 'Strength'
# Enter units (e.g. 'MPa')
unit = 'MPa'

# Program loads the file and calculates Weibull parameters, which are displayed in the pop-up figure
dist = np.loadtxt(filename)  
statistics(dist,varname,unit)      