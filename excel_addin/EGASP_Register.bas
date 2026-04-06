' =======================================================================
' EGASP - 乙二醇水溶液物性参数查询程序
' 纯VBA Excel插件 - 函数注册模块
' =======================================================================

Option Explicit

Public Registered As Boolean

' 注册所有EGASP函数
Public Sub RegisterEGASPFunctions()
    If Registered Then Exit Sub
    Registered = True
    
    On Error Resume Next
    
    ' EG_INITIALIZE
    Application.MacroOptions _
        Macro:="EG_INITIALIZE", _
        Description:="初始化EGASP环境，检查egasp.exe是否可用", _
        Category:="EGASP"
    
    ' EG_PROPERTY
    Application.MacroOptions _
        Macro:="EG_PROPERTY", _
        Description:="通用属性查询函数", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "物性参数类型 (rho/mu/cp/k/mass/volume/freezing/boiling)", _
            "浓度类型 (volume/mass)", _
            "浓度值 (0.1-0.9)", _
            "温度值 (-35~125°C)")
    
    ' EG_RHO
    Application.MacroOptions _
        Macro:="EG_RHO", _
        Description:="获取乙二醇水溶液的密度 (kg/m³)", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "浓度类型 (volume/mass)", _
            "浓度值 (0.1-0.9)", _
            "温度值 (-35~125°C)")
    
    ' EG_MU
    Application.MacroOptions _
        Macro:="EG_MU", _
        Description:="获取乙二醇水溶液的粘度 (Pa·s)", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "浓度类型 (volume/mass)", _
            "浓度值 (0.1-0.9)", _
            "温度值 (-35~125°C)")
    
    ' EG_CP
    Application.MacroOptions _
        Macro:="EG_CP", _
        Description:="获取乙二醇水溶液的比热容 (J/kg·K)", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "浓度类型 (volume/mass)", _
            "浓度值 (0.1-0.9)", _
            "温度值 (-35~125°C)")
    
    ' EG_K
    Application.MacroOptions _
        Macro:="EG_K", _
        Description:="获取乙二醇水溶液的导热系数 (W/m·K)", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "浓度类型 (volume/mass)", _
            "浓度值 (0.1-0.9)", _
            "温度值 (-35~125°C)")
    
    ' EG_TF
    Application.MacroOptions _
        Macro:="EG_TF", _
        Description:="获取乙二醇水溶液的冰点 (°C)", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "浓度类型 (volume/mass)", _
            "浓度值 (0.1-0.9)")
    
    ' EG_TB
    Application.MacroOptions _
        Macro:="EG_TB", _
        Description:="获取乙二醇水溶液的沸点 (°C)", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "浓度类型 (volume/mass)", _
            "浓度值 (0.1-0.9)")
    
    ' EG_MASS
    Application.MacroOptions _
        Macro:="EG_MASS", _
        Description:="计算质量浓度 (%)", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "输入浓度类型 (volume/mass)", _
            "输入浓度值 (0.1-0.9)", _
            "温度值 (-35~125°C)")
    
    ' EG_VOL
    Application.MacroOptions _
        Macro:="EG_VOL", _
        Description:="计算体积浓度 (%)", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "输入浓度类型 (volume/mass)", _
            "输入浓度值 (0.1-0.9)", _
            "温度值 (-35~125°C)")
    
    ' EG_CLEAR_CACHE
    Application.MacroOptions _
        Macro:="EG_CLEAR_CACHE", _
        Description:="清除EGASP计算缓存", _
        Category:="EGASP"
    
    ' EG_TOGGLE_CACHE
    Application.MacroOptions _
        Macro:="EG_TOGGLE_CACHE", _
        Description:="切换缓存启用状态", _
        Category:="EGASP", _
        ArgumentDescriptions:=Array( _
            "是否启用缓存 (TRUE/FALSE)")
    
    ' EG_CACHE_STATUS
    Application.MacroOptions _
        Macro:="EG_CACHE_STATUS", _
        Description:="获取当前缓存状态", _
        Category:="EGASP"
    
    On Error GoTo 0
End Sub

' 工作簿打开时自动注册
Private Sub Workbook_Open()
    Call RegisterEGASPFunctions
End Sub
