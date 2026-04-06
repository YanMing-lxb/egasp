' =======================================================================
' EGASP - 乙二醇水溶液物性参数查询程序
' 纯VBA Excel插件 - 缓存管理模块
' =======================================================================

Option Explicit

' 缓存存储
Private Type CacheItem
    Key As String
    Value As Variant
    TimeStamp As Double
End Type

Private CacheCollection() As CacheItem
Private CacheCount As Integer

' 初始化缓存
Public Sub ClearCache()
    ReDim CacheCollection(0)
    CacheCount = 0
End Sub

' 获取缓存项
Public Function GetCache(ByVal key As String) As Variant
    Dim i As Integer
    For i = 0 To CacheCount - 1
        If CacheCollection(i).Key = key Then
            GetCache = CacheCollection(i).Value
            Exit Function
        End If
    Next i
    GetCache = Empty
End Function

' 设置缓存项
Public Sub SetCache(ByVal key As String, ByVal value As Variant)
    Dim i As Integer
    Dim found As Boolean
    
    ' 检查是否已存在
    found = False
    For i = 0 To CacheCount - 1
        If CacheCollection(i).Key = key Then
            CacheCollection(i).Value = value
            CacheCollection(i).TimeStamp = Timer
            found = True
            Exit For
        End If
    Next i
    
    If Not found Then
        ' 检查缓存大小
        If CacheCount >= CacheSize Then
            ' FIFO 淘汰最旧的项
            For i = 1 To CacheCount - 1
                CacheCollection(i - 1) = CacheCollection(i)
            Next i
            CacheCount = CacheCount - 1
        End If
        
        ' 添加新项
        ReDim Preserve CacheCollection(CacheCount)
        CacheCollection(CacheCount).Key = key
        CacheCollection(CacheCount).Value = value
        CacheCollection(CacheCount).TimeStamp = Timer
        CacheCount = CacheCount + 1
    End If
End Sub

' 获取缓存项数
Public Function GetCacheCount() As Integer
    GetCacheCount = CacheCount
End Function
