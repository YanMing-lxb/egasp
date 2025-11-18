'''
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2025-11-18 09:51:52 +0800
LastEditTime : 2025-11-18 09:52:20 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /egasp/test.py
Description  : 
 -----------------------------------------------------------------------
'''

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 EGASP 类的 prop 方法
"""

import numpy as np
from src.egasp.core import EGASP

def test_prop():
    # 创建 EGASP 实例
    egasp = EGASP()
    
    # 测试用例1: 单个温度值和浓度值
    print("测试用例1: 单个温度值和浓度值")
    temp_single = 25.0
    conc_single = 0.3
    rho_result = egasp.prop(temp=temp_single, conc=conc_single, egp_key='rho')
    print(f"温度: {temp_single}°C, 浓度: {conc_single}, 密度: {rho_result} kg/m³")
    
    cp_result = egasp.prop(temp=temp_single, conc=conc_single, egp_key='cp')
    print(f"温度: {temp_single}°C, 浓度: {conc_single}, 比热容: {cp_result} J/kg·K")
    
    k_result = egasp.prop(temp=temp_single, conc=conc_single, egp_key='k')
    print(f"温度: {temp_single}°C, 浓度: {conc_single}, 导热系数: {k_result} W/m·K")
    
    mu_result = egasp.prop(temp=temp_single, conc=conc_single, egp_key='mu')
    print(f"温度: {temp_single}°C, 浓度: {conc_single}, 动力粘度: {mu_result} Pa·s")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例2: 温度数组和单一浓度值
    print("测试用例2: 温度数组和单一浓度值")
    temp_array = np.array([0, 25, 50, 75, 100])
    conc_single = 0.5
    rho_results = egasp.prop(temp=temp_array, conc=conc_single, egp_key='rho')
    print(f"温度数组: {temp_array}°C, 浓度: {conc_single}")
    print(f"密度结果: {rho_results} kg/m³")
    
    cp_results = egasp.prop(temp=temp_array, conc=conc_single, egp_key='cp')
    print(f"比热容结果: {cp_results} J/kg·K")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例3: 边界值测试
    print("测试用例3: 边界值测试")
    # 最小温度和浓度
    rho_min = egasp.prop(temp=-35, conc=0.1, egp_key='rho')
    print(f"最小温度(-35°C)和最小浓度(0.1)下的密度: {rho_min} kg/m³")
    
    # 最大温度和浓度
    rho_max = egasp.prop(temp=125, conc=0.9, egp_key='rho')
    print(f"最大温度(125°C)和最大浓度(0.9)下的密度: {rho_max} kg/m³")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例4: 插值效果测试
    print("测试用例4: 插值效果测试")
    # 使用非节点值进行测试
    rho_interp = egasp.prop(temp=27.5, conc=0.35, egp_key='rho')
    print(f"温度27.5°C (非节点值) 和浓度0.35 (非节点值) 下的密度: {rho_interp} kg/m³")
    
    print("\n测试完成!")

if __name__ == "__main__":
    test_prop()