' =======================================================================
' EGASP - 乙二醇水溶液物性参数查询程序
' 纯VBA Excel插件 - Ribbon接口模块
' =======================================================================

Option Explicit

' Ribbon对象
Public rib As IRibbonUI

' Ribbon回调 - 初始化
Public Sub EGASP_Ribbon_Load(ribbon As IRibbonUI)
    Set rib = ribbon
    Call EGASP_Initialize
End Sub

' 初始化EGASP按钮回调
Public Sub EGASP_InitializeRibbon(control As IRibbonControl)
    Dim result As String
    result = EG_INITIALIZE()
    MsgBox result, vbInformation, "EGASP 初始化"
End Sub

' 物性参数查询按钮回调
Public Sub EGASP_PropertyQueryRibbon(control As IRibbonControl)
    ' 这里可以显示一个用户窗体
    MsgBox "物性参数查询功能" & vbCrLf & vbCrLf & _
           "在单元格中使用以下函数：" & vbCrLf & _
           "EG_RHO(type, value, temp) - 密度" & vbCrLf & _
           "EG_MU(type, value, temp) - 粘度" & vbCrLf & _
           "EG_CP(type, value, temp) - 比热容" & vbCrLf & _
           "EG_K(type, value, temp) - 导热系数" & vbCrLf & _
           "EG_TF(type, value) - 冰点" & vbCrLf & _
           "EG_TB(type, value) - 沸点", vbInformation, "EGASP 物性参数查询"
End Sub

' 清除缓存按钮回调
Public Sub EGASP_ClearCacheRibbon(control As IRibbonControl)
    Dim result As String
    result = EG_CLEAR_CACHE()
    MsgBox result, vbInformation, "EGASP 缓存"
End Sub

' 缓存状态按钮回调
Public Sub EGASP_CacheStatusRibbon(control As IRibbonControl)
    Dim result As String
    result = EG_CACHE_STATUS()
    MsgBox result, vbInformation, "EGASP 缓存状态"
End Sub

' 关于按钮回调
Public Sub EGASP_AboutRibbon(control As IRibbonControl)
    MsgBox "乙二醇水溶液物性参数查询程序" & vbCrLf & _
           "EGASP (Ethylene Glycol Aqueous Solution Properties)" & vbCrLf & vbCrLf & _
           "版本: 请运行 egasp.exe --version 查看" & vbCrLf & _
           "GitHub: https://github.com/YanMing-lxb/egasp", vbInformation, "关于 EGASP"
End Sub

' 函数向导按钮回调
Public Sub EGASP_FunctionWizardRibbon(control As IRibbonControl)
    On Error Resume Next
    ActiveCell.FunctionWizard
End Sub
