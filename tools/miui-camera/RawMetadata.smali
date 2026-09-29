.class public final Lorg/pixelos/camera/RawMetadata;
.super Ljava/lang/Object;

# AOSP DngCreator reads static white level; MIVI RAW uses per-capture metadata.
.method public static forCapture(Landroid/hardware/camera2/CameraCharacteristics;Landroid/hardware/camera2/CaptureResult;Landroid/util/Size;)Landroid/hardware/camera2/CameraCharacteristics;
    .locals 7

    sget-object v0, Landroid/hardware/camera2/CaptureResult;->SENSOR_DYNAMIC_WHITE_LEVEL:Landroid/hardware/camera2/CaptureResult$Key;
    invoke-virtual {p1, v0}, Landroid/hardware/camera2/CaptureResult;->get(Landroid/hardware/camera2/CaptureResult$Key;)Ljava/lang/Object;
    move-result-object v0
    check-cast v0, Ljava/lang/Integer;
    if-eqz v0, :dimensions

    invoke-virtual {p0}, Landroid/hardware/camera2/CameraCharacteristics;->getNativeCopy()Landroid/hardware/camera2/impl/CameraMetadataNative;
    move-result-object v1
    sget-object v2, Landroid/hardware/camera2/CameraCharacteristics;->SENSOR_INFO_WHITE_LEVEL:Landroid/hardware/camera2/CameraCharacteristics$Key;
    invoke-virtual {v1, v2, v0}, Landroid/hardware/camera2/impl/CameraMetadataNative;->set(Landroid/hardware/camera2/CameraCharacteristics$Key;Ljava/lang/Object;)V
    new-instance p0, Landroid/hardware/camera2/CameraCharacteristics;
    invoke-direct {p0, v1}, Landroid/hardware/camera2/CameraCharacteristics;-><init>(Landroid/hardware/camera2/impl/CameraMetadataNative;)V

    :dimensions
    new-instance v0, Landroid/hardware/camera2/CameraCharacteristics$Key;
    const-string v1, "xiaomi.scaler.availableSuperResolutionStreamConfigurations"
    const-class v2, [I
    invoke-direct {v0, v1, v2}, Landroid/hardware/camera2/CameraCharacteristics$Key;-><init>(Ljava/lang/String;Ljava/lang/Class;)V
    invoke-virtual {p0, v0}, Landroid/hardware/camera2/CameraCharacteristics;->get(Landroid/hardware/camera2/CameraCharacteristics$Key;)Ljava/lang/Object;
    move-result-object v0
    check-cast v0, [I
    if-eqz v0, :unchanged
    invoke-virtual {p2}, Landroid/util/Size;->getWidth()I
    move-result v1
    invoke-virtual {p2}, Landroid/util/Size;->getHeight()I
    move-result v2
    const/4 v3, 0x0

    :next
    add-int/lit8 v4, v3, 0x3
    array-length v5, v0
    if-ge v4, v5, :unchanged
    aget v4, v0, v3
    const/16 v5, 0x20
    if-ne v4, v5, :advance
    add-int/lit8 v4, v3, 0x1
    aget v4, v0, v4
    if-ne v4, v1, :advance
    add-int/lit8 v4, v3, 0x2
    aget v4, v0, v4
    if-ne v4, v2, :advance
    add-int/lit8 v4, v3, 0x3
    aget v4, v0, v4
    if-nez v4, :advance

    # MIVI advertises full-resolution RAW in its vendor map, without standard
    # maximum-resolution sensor arrays. Use that exact output size for DNG.
    invoke-virtual {p0}, Landroid/hardware/camera2/CameraCharacteristics;->getNativeCopy()Landroid/hardware/camera2/impl/CameraMetadataNative;
    move-result-object v0
    sget-object v3, Landroid/hardware/camera2/CameraCharacteristics;->SENSOR_INFO_PIXEL_ARRAY_SIZE:Landroid/hardware/camera2/CameraCharacteristics$Key;
    invoke-virtual {v0, v3, p2}, Landroid/hardware/camera2/impl/CameraMetadataNative;->set(Landroid/hardware/camera2/CameraCharacteristics$Key;Ljava/lang/Object;)V
    new-instance v3, Landroid/graphics/Rect;
    const/4 v4, 0x0
    invoke-direct {v3, v4, v4, v1, v2}, Landroid/graphics/Rect;-><init>(IIII)V
    sget-object v4, Landroid/hardware/camera2/CameraCharacteristics;->SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE:Landroid/hardware/camera2/CameraCharacteristics$Key;
    invoke-virtual {v0, v4, v3}, Landroid/hardware/camera2/impl/CameraMetadataNative;->set(Landroid/hardware/camera2/CameraCharacteristics$Key;Ljava/lang/Object;)V
    sget-object v4, Landroid/hardware/camera2/CameraCharacteristics;->SENSOR_INFO_ACTIVE_ARRAY_SIZE:Landroid/hardware/camera2/CameraCharacteristics$Key;
    invoke-virtual {v0, v4, v3}, Landroid/hardware/camera2/impl/CameraMetadataNative;->set(Landroid/hardware/camera2/CameraCharacteristics$Key;Ljava/lang/Object;)V
    new-instance p0, Landroid/hardware/camera2/CameraCharacteristics;
    invoke-direct {p0, v0}, Landroid/hardware/camera2/CameraCharacteristics;-><init>(Landroid/hardware/camera2/impl/CameraMetadataNative;)V
    return-object p0

    :advance
    add-int/lit8 v3, v3, 0x4
    goto :next

    :unchanged
    return-object p0
.end method
