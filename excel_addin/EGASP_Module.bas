' =======================================================================
' EGASP - 乙二醇水溶液物性参数查询程序
' 纯VBA Excel插件 - 主模块
' =======================================================================

Option Explicit

' 全局变量
Public Initialized As Boolean
Public CacheEnabled As Boolean
Public CacheSize As Integer

' 初始化模块
Private Sub EGASP_Initialize()
    If Not Initialized Then
        Initialized = True
        CacheEnabled = True
        CacheSize = 1000
        Call ClearCache
    End If
End Sub

' 检查egasp.exe是否可用
Private Function CheckEGASP() As Boolean
    On Error GoTo ErrorHandler
    Dim result As String
    result = ShellRun("egasp.exe --version")
    CheckEGASP = (result <> "")
    Exit Function
ErrorHandler:
    CheckEGASP = False
End Function

' 运行命令并返回输出（隐藏窗口）
Private Function ShellRun(cmd As String) As String
    Dim wsh As Object
    Dim tmpFilePath As String
    Dim fileNo As Integer
    Dim result As String
    Dim fullCmd As String
    
    ' 创建临时文件路径
    tmpFilePath = Environ("TEMP") & "\egasp_output.tmp"
    
    ' 构建完整命令，通过 cmd.exe 执行以支持输出重定向
    fullCmd = "cmd.exe /c " & Chr(34) & cmd & " > " & Chr(34) & tmpFilePath & Chr(34) & Chr(34)
    
    ' 创建 Shell 对象
    Set wsh = CreateObject("WScript.Shell")
    
    ' 使用 Run 方法并隐藏窗口（第二个参数为窗口样式，0 表示隐藏）
    wsh.Run fullCmd, 0, True ' 第二个参数 0 表示隐藏窗口，True 表示等待完成
    
    ' 从临时文件中读取输出结果
    On Error Resume Next
    fileNo = FreeFile
    Open tmpFilePath For Input As #fileNo
    If Err.Number = 0 Then
        If LOF(fileNo) > 0 Then
            result = Input$(LOF(fileNo), fileNo)
        End If
        Close #fileNo
    End If
    On Error GoTo 0
    
    ' 删除临时文件
    On Error Resume Next
    Kill tmpFilePath
    On Error GoTo 0
    
    ' 清理对象
    Set wsh = Nothing
    
    ' 返回结果
    ShellRun = Trim(result)
End Function

' 通过egasp.exe计算物性参数
Private Function CalculateProperty(ByVal propType As String, _
                                  ByVal concType As String, _
                                  ByVal concValue As Double, _
                                  ByVal temp As Double) As Variant
    On Error GoTo ErrorHandler
    
    ' 初始化
    Call EGASP_Initialize
    
    ' 检查缓存
    Dim cacheKey As String
    cacheKey = concType & ":" & Format(concValue, "0.000000") & ":" & Format(temp, "0.00") & ":" & propType
    
    If CacheEnabled Then
        Dim cachedResult As Variant
        cachedResult = GetCache(cacheKey)
        If Not IsEmpty(cachedResult) Then
            CalculateProperty = cachedResult
            Exit Function
        End If
    End If
    
    ' 检查egasp.exe是否可用
    If Not CheckEGASP() Then
        CalculateProperty = "#ERROR: 未找到EGASP可执行文件路径"
        Exit Function
    End If
    
    ' 构建命令
    Dim cmd As String
    cmd = "egasp.exe --excel --single --type=" & concType & " --value=" & concValue & " --temp=" & temp & " --prop=" & propType & " --quiet"
    
    ' 执行命令
    Dim result As String
    result = Trim(ShellRun(cmd))
    
    ' 检查结果
    If Left(result, 7) = "#ERROR:" Then
        CalculateProperty = result
    Else
        ' 转换为数值
        On Error Resume Next
        Dim numResult As Double
        numResult = CDbl(result)
        If Err.Number = 0 Then
            CalculateProperty = numResult
            ' 存入缓存
            If CacheEnabled Then
                Call SetCache(cacheKey, numResult)
            End If
        Else
            CalculateProperty = "#ERROR: 结果转换失败"
        End If
        On Error GoTo ErrorHandler
    End If
    
    Exit Function
    
ErrorHandler:
    CalculateProperty = "#ERROR: " & Err.Description
End Function

' ============================================================
' 公开函数 - 供Excel单元格调用
' ============================================================

' 初始化EGASP
Public Function EG_INITIALIZE() As String
    Call EGASP_Initialize
    If CheckEGASP() Then
        EG_INITIALIZE = "EGASP 初始化成功"
    Else
        EG_INITIALIZE = "#ERROR: 未找到EGASP可执行文件路径"
    End If
End Function

' 通用属性查询
Public Function EG_PROPERTY(ByVal propType As String, _
                            ByVal concType As String, _
                            ByVal concValue As Double, _
                            ByVal temp As Double) As Variant
    EG_PROPERTY = CalculateProperty(propType, concType, concValue, temp)
End Function

' 获取密度
Public Function EG_RHO(ByVal concType As String, _
                       ByVal concValue As Double, _
                       ByVal temp As Double) As Variant
    EG_RHO = CalculateProperty("rho", concType, concValue, temp)
End Function

' 获取粘度
Public Function EG_MU(ByVal concType As String, _
                      ByVal concValue As Double, _
                      ByVal temp As Double) As Variant
    EG_MU = CalculateProperty("mu", concType, concValue, temp)
End Function

' 获取比热容
Public Function EG_CP(ByVal concType As String, _
                      ByVal concValue As Double, _
                      ByVal temp As Double) As Variant
    EG_CP = CalculateProperty("cp", concType, concValue, temp)
End Function

' 获取导热系数
Public Function EG_K(ByVal concType As String, _
                     ByVal concValue As Double, _
                     ByVal temp As Double) As Variant
    EG_K = CalculateProperty("k", concType, concValue, temp)
End Function

' 获取冰点
Public Function EG_TF(ByVal concType As String, _
                      ByVal concValue As Double) As Variant
    EG_TF = CalculateProperty("freezing", concType, concValue, 25)
End Function

' 获取沸点
Public Function EG_TB(ByVal concType As String, _
                      ByVal concValue As Double) As Variant
    EG_TB = CalculateProperty("boiling", concType, concValue, 25)
End Function

' 计算质量浓度
Public Function EG_MASS(ByVal concType As String, _
                        ByVal concValue As Double, _
                        ByVal temp As Double) As Variant
    EG_MASS = CalculateProperty("mass", concType, concValue, temp)
End Function

' 计算体积浓度
Public Function EG_VOL(ByVal concType As String, _
                       ByVal concValue As Double, _
                       ByVal temp As Double) As Variant
    EG_VOL = CalculateProperty("volume", concType, concValue, temp)
End Function

' 清除缓存
Public Function EG_CLEAR_CACHE() As String
    Call ClearCache
    EG_CLEAR_CACHE = "缓存已清除"
End Function

' 切换缓存状态
Public Function EG_TOGGLE_CACHE(ByVal enabled As Boolean) As String
    CacheEnabled = enabled
    If CacheEnabled Then
        EG_TOGGLE_CACHE = "缓存已启用"
    Else
        EG_TOGGLE_CACHE = "缓存已禁用"
    End If
End Function

' 获取缓存状态
Public Function EG_CACHE_STATUS() As String
    Dim status As String
    If CacheEnabled Then
        status = "启用"
    Else
        status = "禁用"
    End If
    EG_CACHE_STATUS = "缓存状态: " & status & ", 缓存项数: " & GetCacheCount()
End Function
