.class public final Lorg/pixelos/camera/LensCameraHandoff;
.super Landroid/hardware/camera2/CameraManager$AvailabilityCallback;
.implements Ljava/lang/Runnable;

# Lens launch is recorded on the UI thread. The availability callback, timeout,
# and deferred opens run on the app's camera handler.
.field private static volatile pending:Z
.field private static waiting:Lorg/pixelos/camera/LensCameraHandoff;
.field private final manager:Landroid/hardware/camera2/CameraManager;
.field private final handler:Landroid/os/Handler;

.method private constructor <init>(Landroid/hardware/camera2/CameraManager;Landroid/os/Handler;)V
    .locals 0

    invoke-direct {p0}, Landroid/hardware/camera2/CameraManager$AvailabilityCallback;-><init>()V
    iput-object p1, p0, Lorg/pixelos/camera/LensCameraHandoff;->manager:Landroid/hardware/camera2/CameraManager;
    iput-object p2, p0, Lorg/pixelos/camera/LensCameraHandoff;->handler:Landroid/os/Handler;
    return-void
.end method

.method public static launched()V
    .locals 1

    const/4 v0, 0x1
    sput-boolean v0, Lorg/pixelos/camera/LensCameraHandoff;->pending:Z
    return-void
.end method

.method public static shouldWait(Landroid/hardware/camera2/CameraManager;Landroid/os/Handler;)Z
    .locals 3

    sget-object v0, Lorg/pixelos/camera/LensCameraHandoff;->waiting:Lorg/pixelos/camera/LensCameraHandoff;
    if-nez v0, :wait
    sget-boolean v0, Lorg/pixelos/camera/LensCameraHandoff;->pending:Z
    if-eqz v0, :open

    const/4 v0, 0x0
    sput-boolean v0, Lorg/pixelos/camera/LensCameraHandoff;->pending:Z
    new-instance v0, Lorg/pixelos/camera/LensCameraHandoff;
    invoke-direct {v0, p0, p1}, Lorg/pixelos/camera/LensCameraHandoff;-><init>(Landroid/hardware/camera2/CameraManager;Landroid/os/Handler;)V
    sput-object v0, Lorg/pixelos/camera/LensCameraHandoff;->waiting:Lorg/pixelos/camera/LensCameraHandoff;
    invoke-virtual {p0, v0, p1}, Landroid/hardware/camera2/CameraManager;->registerAvailabilityCallback(Landroid/hardware/camera2/CameraManager$AvailabilityCallback;Landroid/os/Handler;)V

    # Resume normal error handling if the scanner does not give up its camera.
    const-wide/16 v1, 0x5dc
    invoke-virtual {p1, v0, v1, v2}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    const-string v0, "LensCameraHandoff"
    const-string v1, "Waiting for Google Lens camera 0 to become available"
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    :wait
    const/4 v0, 0x1
    return v0

    :open
    const/4 v0, 0x0
    return v0
.end method

.method public onCameraAvailable(Ljava/lang/String;)V
    .locals 2

    const-string v0, "0"
    invoke-virtual {v0, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :done

    const-string v0, "LensCameraHandoff"
    const-string v1, "Google Lens camera 0 available"
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    invoke-direct {p0}, Lorg/pixelos/camera/LensCameraHandoff;->stopWaiting()V

    :done
    return-void
.end method

.method public run()V
    .locals 2

    const-string v0, "LensCameraHandoff"
    const-string v1, "Timed out waiting for Google Lens camera 0"
    invoke-static {v0, v1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I
    invoke-direct {p0}, Lorg/pixelos/camera/LensCameraHandoff;->stopWaiting()V
    return-void
.end method

.method private stopWaiting()V
    .locals 1

    iget-object v0, p0, Lorg/pixelos/camera/LensCameraHandoff;->manager:Landroid/hardware/camera2/CameraManager;
    invoke-virtual {v0, p0}, Landroid/hardware/camera2/CameraManager;->unregisterAvailabilityCallback(Landroid/hardware/camera2/CameraManager$AvailabilityCallback;)V
    iget-object v0, p0, Lorg/pixelos/camera/LensCameraHandoff;->handler:Landroid/os/Handler;
    invoke-virtual {v0, p0}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    sget-object v0, Lorg/pixelos/camera/LensCameraHandoff;->waiting:Lorg/pixelos/camera/LensCameraHandoff;
    if-ne v0, p0, :done
    const/4 v0, 0x0
    sput-object v0, Lorg/pixelos/camera/LensCameraHandoff;->waiting:Lorg/pixelos/camera/LensCameraHandoff;

    :done
    return-void
.end method
