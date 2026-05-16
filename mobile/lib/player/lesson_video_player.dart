import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';
import 'package:vector_math/vector_math_64.dart' as vector;

import '../app_localization.dart';
import 'fullscreen_video_screen.dart';
import 'video_player_overlays.dart';

enum InlineVideoPreviewMode { native, loading, embedded, error }

bool _isSupportedVideoUrl(String url) {
  final parsed = Uri.tryParse(url);
  if (parsed == null || !parsed.hasScheme) {
    return false;
  }
  final path = parsed.path.toLowerCase();
  return path.endsWith('.mp4') || path.endsWith('.webm');
}

class InlineVideoPanel extends StatefulWidget {
  const InlineVideoPanel({
    super.key,
    required this.url,
    required this.title,
    this.initialPositionSeconds = 0,
    this.onPositionChanged,
    this.previewMode,
    this.errorText,
  });

  final String url;
  final String title;
  final int initialPositionSeconds;
  final ValueChanged<int>? onPositionChanged;
  final InlineVideoPreviewMode? previewMode;
  final String? errorText;

  @override
  State<InlineVideoPanel> createState() => _InlineVideoPanelState();
}

class _InlineVideoPanelState extends State<InlineVideoPanel> {
  @override
  Widget build(BuildContext context) {
    return _LessonVideoPlayerShell(
      url: widget.url,
      title: widget.title,
      initialPositionSeconds: widget.initialPositionSeconds,
      onPositionChanged: widget.onPositionChanged,
      previewMode: widget.previewMode,
      errorText: widget.errorText,
    );
  }
}

class _LessonVideoPlayerShell extends StatefulWidget {
  const _LessonVideoPlayerShell({
    required this.url,
    required this.title,
    this.initialPositionSeconds = 0,
    this.onPositionChanged,
    this.previewMode,
    this.errorText,
    this.fullscreen = false,
    this.existingController,
    this.initialFitMode = VideoFitMode.contain,
    this.initialPreviewIsPlaying = false,
  });

  final String url;
  final String title;
  final int initialPositionSeconds;
  final ValueChanged<int>? onPositionChanged;
  final InlineVideoPreviewMode? previewMode;
  final String? errorText;
  final bool fullscreen;
  final VideoPlayerController? existingController;
  final VideoFitMode initialFitMode;
  final bool initialPreviewIsPlaying;

  @override
  State<_LessonVideoPlayerShell> createState() =>
      _LessonVideoPlayerShellState();
}

class _LessonVideoPlayerShellState extends State<_LessonVideoPlayerShell> {
  static const _autoHideDelay = Duration(seconds: 3);
  static const _previewDuration = Duration(seconds: 13);
  static const _previewTick = Duration(milliseconds: 250);

  VideoPlayerController? _controller;
  Timer? _overlayHideTimer;
  Timer? _previewPlaybackTimer;

  bool _ownsController = false;
  bool _controlsVisible = true;
  bool _loading = true;
  bool _previewPlaying = false;
  bool _lastControllerPlaying = false;
  bool _lastControllerBuffering = false;
  bool _didReachEnd = false;
  bool _showResumePrompt = false;
  bool _resumeSeeking = false;

  TapDownDetails? _lastDoubleTapDownDetails;
  TransformationController? _fullscreenTransformationController;
  Duration _previewPosition = Duration.zero;
  int _lastReportedSeconds = 0;
  int _lastNativePositionMilliseconds = 0;
  double _zoomScale = 1;
  String? _error;
  late VideoFitMode _fitMode;

  bool get _isPreview => widget.previewMode == InlineVideoPreviewMode.embedded;

  bool get _isErrorPreview =>
      widget.previewMode == InlineVideoPreviewMode.error;

  bool get _isLoadingPreview =>
      widget.previewMode == InlineVideoPreviewMode.loading;

  bool get _isNativeMode =>
      widget.previewMode == null ||
      widget.previewMode == InlineVideoPreviewMode.native;

  bool get _isPlaying {
    if (_isPreview) {
      return _previewPlaying;
    }
    return _controller?.value.isPlaying ?? false;
  }

  bool get _isBuffering {
    if (_isPreview || _loading || _error != null) {
      return false;
    }
    return _resumeSeeking || (_controller?.value.isBuffering ?? false);
  }

  Duration get _position {
    if (_isPreview) {
      return _previewPosition;
    }
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return Duration.zero;
    }
    return controller.value.position;
  }

  Duration get _duration {
    if (_isPreview) {
      return _previewDuration;
    }
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return Duration.zero;
    }
    return controller.value.duration;
  }

  double get _aspectRatio {
    if (_isPreview) {
      return 16 / 9;
    }
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return 16 / 9;
    }
    return controller.value.aspectRatio <= 0
        ? 16 / 9
        : controller.value.aspectRatio;
  }

  @override
  void initState() {
    super.initState();
    _fitMode = widget.initialFitMode;
    _previewPosition = Duration(seconds: widget.initialPositionSeconds);
    _previewPlaying = widget.initialPreviewIsPlaying;
    if (widget.fullscreen) {
      _initializeFullscreenZoom();
    }
    _initializePlayer();
  }

  @override
  void didUpdateWidget(covariant _LessonVideoPlayerShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.url != widget.url ||
        oldWidget.previewMode != widget.previewMode ||
        oldWidget.existingController != widget.existingController) {
      _releaseController();
      _overlayHideTimer?.cancel();
      _previewPlaybackTimer?.cancel();
      _controlsVisible = true;
      _previewPosition = Duration(seconds: widget.initialPositionSeconds);
      _previewPlaying = widget.initialPreviewIsPlaying;
      _fitMode = widget.initialFitMode;
      _lastReportedSeconds = 0;
      _loading = true;
      _error = null;
      _didReachEnd = false;
      _lastControllerPlaying = false;
      _lastControllerBuffering = false;
      _showResumePrompt = false;
      _resumeSeeking = false;
      _zoomScale = 1;
      if (widget.fullscreen && _fullscreenTransformationController == null) {
        _initializeFullscreenZoom();
      }
      _initializePlayer();
    }
  }

  void _initializeFullscreenZoom() {
    _fullscreenTransformationController?.removeListener(_handleZoomChanged);
    _fullscreenTransformationController?.dispose();
    _fullscreenTransformationController =
        TransformationController(vector.Matrix4.identity())
          ..addListener(_handleZoomChanged);
  }

  void _handleZoomChanged() {
    final controller = _fullscreenTransformationController;
    if (controller == null) {
      return;
    }
    final nextScale = controller.value.getMaxScaleOnAxis();
    if ((nextScale - _zoomScale).abs() < 0.01) {
      return;
    }
    if (mounted) {
      setState(() => _zoomScale = nextScale);
    } else {
      _zoomScale = nextScale;
    }
  }

  void _resetZoom() {
    final controller = _fullscreenTransformationController;
    if (controller == null) {
      return;
    }
    controller.value = vector.Matrix4.identity();
    if (mounted) {
      setState(() => _zoomScale = 1);
    } else {
      _zoomScale = 1;
    }
    _showControls();
  }

  void _storeDoubleTapDown(TapDownDetails details) {
    _lastDoubleTapDownDetails = details;
  }

  void _toggleQuickZoom() {
    final controller = _fullscreenTransformationController;
    if (controller == null) {
      return;
    }
    if (_zoomScale > 1.05) {
      _resetZoom();
      return;
    }
    final tapPosition =
        _lastDoubleTapDownDetails?.localPosition ?? const Offset(0, 0);
    const targetScale = 2.0;
    controller.value = vector.Matrix4.identity()
      ..translateByVector3(
        vector.Vector3(
          -tapPosition.dx * (targetScale - 1),
          -tapPosition.dy * (targetScale - 1),
          0,
        ),
      )
      ..scaleByVector3(vector.Vector3(targetScale, targetScale, 1));
    if (mounted) {
      setState(() => _zoomScale = targetScale);
    } else {
      _zoomScale = targetScale;
    }
    _showControls();
  }

  void _initializePlayer() {
    if (_isLoadingPreview) {
      setState(() {
        _loading = true;
        _error = null;
      });
      return;
    }

    if (_isErrorPreview) {
      setState(() {
        _loading = false;
        _error = widget.errorText ??
            AppLanguageRuntime.strings.videoCouldNotBeLoaded();
      });
      return;
    }

    if (_isPreview) {
      setState(() {
        _loading = false;
        _error = null;
      });
      if (_previewPlaying) {
        _startPreviewPlayback();
      }
      return;
    }

    _initializeNative();
  }

  Future<void> _initializeNative() async {
    if (!_isSupportedVideoUrl(widget.url)) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = widget.errorText ??
              AppLanguageRuntime.strings.unsupportedVideoSource;
        });
      }
      return;
    }

    final sharedController = widget.existingController;
    if (sharedController != null) {
      _controller = sharedController;
      _ownsController = false;
      _controller?.addListener(_handleControllerChanged);
      if (mounted) {
        setState(() {
          _loading = false;
          _error = null;
          _lastControllerPlaying = _controller?.value.isPlaying ?? false;
          _lastControllerBuffering = _controller?.value.isBuffering ?? false;
          _lastNativePositionMilliseconds =
              _controller?.value.position.inMilliseconds ?? 0;
        });
      }
      _syncOverlayVisibility();
      return;
    }

    final parsed = Uri.tryParse(widget.url);
    if (parsed == null) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error =
              widget.errorText ?? AppLanguageRuntime.strings.invalidVideoUrl;
        });
      }
      return;
    }

    final controller = VideoPlayerController.networkUrl(parsed);
    _controller = controller;
    _ownsController = true;

    try {
      await controller.initialize();
      controller.addListener(_handleControllerChanged);
      if (!mounted) {
        controller.removeListener(_handleControllerChanged);
        await controller.dispose();
        return;
      }
      final resumePosition = _initialResumePositionFor(controller);
      setState(() {
        _loading = false;
        _error = null;
        _showResumePrompt = resumePosition != null;
        _resumeSeeking = false;
        _lastControllerPlaying = controller.value.isPlaying;
        _lastControllerBuffering = controller.value.isBuffering;
        _lastNativePositionMilliseconds =
            controller.value.position.inMilliseconds;
      });
      _syncOverlayVisibility(forceVisible: true);
    } catch (exception) {
      controller.removeListener(_handleControllerChanged);
      await controller.dispose();
      if (mounted) {
        setState(() {
          _loading = false;
          _error = widget.errorText ??
              AppLanguageRuntime.strings.videoCouldNotBeLoaded(
                exception.toString(),
              );
        });
      }
    }
  }

  Duration? _initialResumePositionFor(VideoPlayerController controller) {
    if (widget.initialPositionSeconds <= 0 || !controller.value.isInitialized) {
      return null;
    }
    final duration = controller.value.duration;
    if (duration <= Duration.zero) {
      return Duration(seconds: widget.initialPositionSeconds);
    }
    final target = Duration(seconds: widget.initialPositionSeconds);
    final maxResumePosition = duration - const Duration(seconds: 1);
    if (maxResumePosition <= Duration.zero) {
      return null;
    }
    return target > maxResumePosition ? maxResumePosition : target;
  }

  Future<void> _resumeFromSavedPosition() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return;
    }
    final target = _initialResumePositionFor(controller);
    if (target == null) {
      setState(() {
        _showResumePrompt = false;
        _resumeSeeking = false;
      });
      return;
    }

    setState(() => _resumeSeeking = true);
    _showControls(restartTimer: false);
    try {
      await controller.seekTo(target);
      _reportPosition(target.inSeconds);
      if (!mounted || _controller != controller) {
        return;
      }
      setState(() {
        _showResumePrompt = false;
        _resumeSeeking = false;
        _lastControllerBuffering = controller.value.isBuffering;
        _lastNativePositionMilliseconds =
            controller.value.position.inMilliseconds;
      });
    } catch (_) {
      if (mounted && _controller == controller) {
        setState(() => _resumeSeeking = false);
      }
    }
  }

  void _handleControllerChanged() {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return;
    }

    _reportPosition(controller.value.position.inSeconds);

    final position = controller.value.position;
    final duration = controller.value.duration;
    final didReachEnd = duration > Duration.zero && position >= duration;
    final isPlaying = controller.value.isPlaying;
    final isBuffering = controller.value.isBuffering;
    final positionMilliseconds = position.inMilliseconds;
    final didStatusChange =
        didReachEnd != _didReachEnd || isPlaying != _lastControllerPlaying;
    final didBufferingChange = isBuffering != _lastControllerBuffering;
    final didPositionChange =
        positionMilliseconds != _lastNativePositionMilliseconds;

    if (didStatusChange || didBufferingChange || didPositionChange) {
      if (mounted) {
        setState(() {
          _didReachEnd = didReachEnd;
          _lastControllerPlaying = isPlaying;
          _lastControllerBuffering = isBuffering;
          _lastNativePositionMilliseconds = positionMilliseconds;
        });
      } else {
        _didReachEnd = didReachEnd;
        _lastControllerPlaying = isPlaying;
        _lastControllerBuffering = isBuffering;
        _lastNativePositionMilliseconds = positionMilliseconds;
      }
    }

    if (didStatusChange) {
      _syncOverlayVisibility(forceVisible: !isPlaying || didReachEnd);
    }
  }

  void _syncOverlayVisibility({bool forceVisible = false}) {
    final shouldShow =
        forceVisible || !_isPlaying || _didReachEnd || _error != null;
    if (shouldShow) {
      _showControls(restartTimer: false);
    } else {
      _scheduleAutoHide();
    }
  }

  void _showControls({bool restartTimer = true}) {
    if (!_controlsVisible && mounted) {
      setState(() => _controlsVisible = true);
    }
    if (restartTimer) {
      _scheduleAutoHide();
    } else {
      _overlayHideTimer?.cancel();
    }
  }

  void _hideControls() {
    if (_controlsVisible && mounted) {
      setState(() => _controlsVisible = false);
    }
    _overlayHideTimer?.cancel();
  }

  void _scheduleAutoHide() {
    _overlayHideTimer?.cancel();
    if (!_isPlaying || _didReachEnd || _error != null) {
      return;
    }
    _overlayHideTimer = Timer(_autoHideDelay, _hideControls);
  }

  void _toggleControlsVisibility() {
    if (_controlsVisible) {
      _hideControls();
    } else {
      _showControls();
    }
  }

  void _startPreviewPlayback() {
    _previewPlaybackTimer?.cancel();
    _previewPlaybackTimer = Timer.periodic(_previewTick, (_) {
      if (!mounted || !_previewPlaying) {
        return;
      }
      final next = _previewPosition + _previewTick;
      if (next >= _previewDuration) {
        _previewPosition = _previewDuration;
        _previewPlaying = false;
        _didReachEnd = true;
        _previewPlaybackTimer?.cancel();
        _reportPosition(_previewPosition.inSeconds);
        setState(() {});
        _showControls(restartTimer: false);
        return;
      }
      _previewPosition = next;
      _didReachEnd = false;
      _reportPosition(_previewPosition.inSeconds);
      setState(() {});
    });
  }

  Future<void> _togglePlayPause() async {
    _showControls();
    if (_isPreview) {
      if (_previewPlaying) {
        _previewPlaying = false;
        _previewPlaybackTimer?.cancel();
        setState(() {});
        _showControls(restartTimer: false);
        return;
      }
      if (_previewPosition >= _previewDuration) {
        _previewPosition = Duration.zero;
      }
      _previewPlaying = true;
      _didReachEnd = false;
      setState(() {});
      _startPreviewPlayback();
      _scheduleAutoHide();
      return;
    }

    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return;
    }
    if (_showResumePrompt && !_resumeSeeking && mounted) {
      setState(() => _showResumePrompt = false);
    }
    if (controller.value.isPlaying) {
      await controller.pause();
      if (mounted) {
        setState(() {
          _lastControllerPlaying = controller.value.isPlaying;
          _lastNativePositionMilliseconds =
              controller.value.position.inMilliseconds;
        });
      }
      _showControls(restartTimer: false);
    } else {
      if (controller.value.position >= controller.value.duration &&
          controller.value.duration > Duration.zero) {
        await controller.seekTo(Duration.zero);
      }
      await controller.play();
      if (mounted) {
        setState(() {
          _lastControllerPlaying = controller.value.isPlaying;
          _lastNativePositionMilliseconds =
              controller.value.position.inMilliseconds;
        });
      }
      _scheduleAutoHide();
    }
  }

  Future<void> _seekTo(Duration target) async {
    _showControls();
    if (_showResumePrompt && mounted) {
      setState(() {
        _showResumePrompt = false;
        _resumeSeeking = false;
      });
    }
    if (_isPreview) {
      final clamped = Duration(
        milliseconds:
            target.inMilliseconds.clamp(0, _previewDuration.inMilliseconds),
      );
      setState(() {
        _previewPosition = clamped;
        _didReachEnd = clamped >= _previewDuration;
      });
      _reportPosition(clamped.inSeconds);
      if (_previewPlaying) {
        _scheduleAutoHide();
      }
      return;
    }

    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return;
    }
    final duration = controller.value.duration;
    final clamped = Duration(
      milliseconds: target.inMilliseconds.clamp(
        0,
        duration.inMilliseconds <= 0 ? 0 : duration.inMilliseconds,
      ),
    );
    await controller.seekTo(clamped);
    _reportPosition(clamped.inSeconds);
    if (mounted) {
      setState(() {
        _lastNativePositionMilliseconds = clamped.inMilliseconds;
      });
    }
    if (controller.value.isPlaying) {
      _scheduleAutoHide();
    }
  }

  Future<void> _seekBy(Duration delta) => _seekTo(_position + delta);

  void _reportPosition(int seconds) {
    if (widget.onPositionChanged == null) {
      return;
    }
    if (seconds == _lastReportedSeconds &&
        seconds != 0 &&
        seconds != _duration.inSeconds) {
      return;
    }
    if ((seconds - _lastReportedSeconds).abs() < 5 &&
        seconds != 0 &&
        seconds != _duration.inSeconds) {
      return;
    }
    _lastReportedSeconds = seconds;
    widget.onPositionChanged?.call(seconds);
  }

  Future<void> _toggleFullscreen() async {
    if (!mounted) {
      return;
    }
    if (widget.fullscreen) {
      Navigator.of(context).pop(_fitMode);
      return;
    }

    final result = await Navigator.of(context).push<VideoFitMode>(
      MaterialPageRoute<VideoFitMode>(
        builder: (_) => FullscreenVideoScreen(
          child: _LessonVideoPlayerShell(
            url: widget.url,
            title: widget.title,
            initialPositionSeconds: _position.inSeconds,
            onPositionChanged: null,
            previewMode: _isPreview
                ? InlineVideoPreviewMode.embedded
                : widget.previewMode,
            errorText: widget.errorText,
            fullscreen: true,
            existingController: _controller,
            initialFitMode: _fitMode,
            initialPreviewIsPlaying: _isPreview ? _previewPlaying : false,
          ),
        ),
      ),
    );

    if (result != null && mounted) {
      setState(() => _fitMode = result);
    }
  }

  void _toggleFitMode() {
    if (_zoomScale > 1.05) {
      _resetZoom();
    }
    setState(() => _fitMode = _fitMode.toggled);
    _showControls();
  }

  Future<void> _retry() async {
    _overlayHideTimer?.cancel();
    _previewPlaybackTimer?.cancel();
    _releaseController();
    setState(() {
      _loading = true;
      _error = null;
      _previewPosition = Duration(seconds: widget.initialPositionSeconds);
      _previewPlaying = false;
      _didReachEnd = false;
      _controlsVisible = true;
      _lastReportedSeconds = 0;
      _lastControllerBuffering = false;
      _showResumePrompt = false;
      _resumeSeeking = false;
    });
    _initializePlayer();
  }

  void _releaseController() {
    final controller = _controller;
    if (controller != null) {
      controller.removeListener(_handleControllerChanged);
      if (_ownsController) {
        unawaited(controller.dispose());
      }
    }
    _controller = null;
    _ownsController = false;
  }

  @override
  void dispose() {
    _overlayHideTimer?.cancel();
    _previewPlaybackTimer?.cancel();
    widget.onPositionChanged?.call(_position.inSeconds);
    _fullscreenTransformationController?.removeListener(_handleZoomChanged);
    _fullscreenTransformationController?.dispose();
    _releaseController();
    super.dispose();
  }

  KeyEventResult _handleKeyboardAction(_PlayerAction action) {
    switch (action) {
      case _PlayerAction.togglePlayPause:
        unawaited(_togglePlayPause());
        return KeyEventResult.handled;
      case _PlayerAction.seekBack:
        unawaited(_seekBy(const Duration(seconds: -10)));
        return KeyEventResult.handled;
      case _PlayerAction.seekForward:
        unawaited(_seekBy(const Duration(seconds: 10)));
        return KeyEventResult.handled;
      case _PlayerAction.toggleFullscreen:
        if (widget.fullscreen || !_loading) {
          unawaited(_toggleFullscreen());
          return KeyEventResult.handled;
        }
        return KeyEventResult.ignored;
      case _PlayerAction.exitFullscreen:
        if (widget.fullscreen) {
          Navigator.of(context).pop(_fitMode);
          return KeyEventResult.handled;
        }
        return KeyEventResult.ignored;
    }
  }

  @override
  Widget build(BuildContext context) {
    final keyboardShortcuts = <ShortcutActivator, Intent>{
      const SingleActivator(LogicalKeyboardKey.space): const _PlayerIntent(
        _PlayerAction.togglePlayPause,
      ),
      const SingleActivator(LogicalKeyboardKey.keyK): const _PlayerIntent(
        _PlayerAction.togglePlayPause,
      ),
      const SingleActivator(LogicalKeyboardKey.arrowLeft): const _PlayerIntent(
        _PlayerAction.seekBack,
      ),
      const SingleActivator(LogicalKeyboardKey.arrowRight): const _PlayerIntent(
        _PlayerAction.seekForward,
      ),
      const SingleActivator(LogicalKeyboardKey.keyF): const _PlayerIntent(
        _PlayerAction.toggleFullscreen,
      ),
      if (widget.fullscreen)
        const SingleActivator(LogicalKeyboardKey.escape): const _PlayerIntent(
          _PlayerAction.exitFullscreen,
        ),
    };

    final actions = <Type, Action<Intent>>{
      _PlayerIntent: CallbackAction<_PlayerIntent>(
        onInvoke: (intent) => _handleKeyboardAction(intent.action),
      ),
    };

    return Shortcuts(
      shortcuts: keyboardShortcuts,
      child: Actions(
        actions: actions,
        child: FocusableActionDetector(
          autofocus: widget.fullscreen,
          child: _buildContent(context),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context) {
    final strings = context.strings;
    if (_loading) {
      return _VideoStatusCard(
        height: widget.fullscreen ? null : 220,
        child: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null) {
      return _VideoStatusCard(
        height: widget.fullscreen ? null : 220,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, color: Colors.white70),
                const SizedBox(height: 12),
                Text(
                  _error!,
                  key: const ValueKey('video-error-message'),
                  textAlign: TextAlign.center,
                  style: Theme.of(context)
                      .textTheme
                      .bodyMedium
                      ?.copyWith(color: Colors.white),
                ),
                const SizedBox(height: 16),
                if (_isNativeMode)
                  FilledButton(
                    onPressed: _retry,
                    child: Text(strings.retry),
                  ),
              ],
            ),
          ),
        ),
      );
    }

    Widget surface = LessonVideoViewport(
      aspectRatio: _aspectRatio,
      fitMode: _fitMode,
      fullscreen: widget.fullscreen,
      child: _isPreview
          ? _PreviewVideoSurface(isPlaying: _previewPlaying)
          : VideoPlayer(_controller!),
    );

    if (widget.fullscreen && _fullscreenTransformationController != null) {
      final canPanZoomedVideo = _zoomScale > 1.05;
      surface = InteractiveViewer(
        key: const ValueKey('fullscreen-zoom-surface'),
        transformationController: _fullscreenTransformationController,
        minScale: 1,
        maxScale: 3,
        boundaryMargin:
            canPanZoomedVideo ? const EdgeInsets.all(120) : EdgeInsets.zero,
        panEnabled: canPanZoomedVideo,
        scaleEnabled: true,
        clipBehavior: Clip.hardEdge,
        child: surface,
      );
    }

    final player = LessonVideoFrame(
      title: widget.title,
      surface: surface,
      position: _position,
      duration: _duration,
      isPlaying: _isPlaying,
      controlsVisible: _controlsVisible,
      buffering: _isBuffering,
      fullscreen: widget.fullscreen,
      fitMode: _fitMode,
      isZoomed: widget.fullscreen && _zoomScale > 1.05,
      zoomLabel: '${_zoomScale.toStringAsFixed(1)}x',
      resumePosition:
          _showResumePrompt ? _initialResumePositionFor(_controller!) : null,
      resumeSeeking: _resumeSeeking,
      onResumeFromPosition: _showResumePrompt
          ? () => unawaited(_resumeFromSavedPosition())
          : null,
      onSurfaceTap: _toggleControlsVisibility,
      onSurfaceDoubleTap: widget.fullscreen ? _toggleQuickZoom : null,
      onSurfaceDoubleTapDown: widget.fullscreen ? _storeDoubleTapDown : null,
      onPlayPause: () => unawaited(_togglePlayPause()),
      onReplay10: () => unawaited(_seekBy(const Duration(seconds: -10))),
      onForward10: () => unawaited(_seekBy(const Duration(seconds: 10))),
      onSeek: (value) => unawaited(
        _seekTo(Duration(milliseconds: value.round())),
      ),
      onResetZoom: widget.fullscreen ? _resetZoom : null,
      onToggleFullscreen:
          widget.fullscreen || !_loading ? _toggleFullscreen : null,
      onToggleFitMode: widget.fullscreen ? _toggleFitMode : null,
    );

    if (widget.fullscreen) {
      return player;
    }

    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: player,
      ),
    );
  }
}

class _VideoStatusCard extends StatelessWidget {
  const _VideoStatusCard({
    required this.child,
    this.height,
  });

  final Widget child;
  final double? height;

  @override
  Widget build(BuildContext context) {
    final content = ColoredBox(
      color: Colors.black,
      child: child,
    );

    if (height == null) {
      return SizedBox.expand(child: content);
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: SizedBox(height: height, child: content),
    );
  }
}

class _PreviewVideoSurface extends StatelessWidget {
  const _PreviewVideoSurface({
    required this.isPlaying,
  });

  final bool isPlaying;

  @override
  Widget build(BuildContext context) {
    final strings = context.strings;
    return Container(
      key: const ValueKey('embedded-video'),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF203A43),
            Color(0xFF2C5364),
          ],
        ),
      ),
      alignment: Alignment.center,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            isPlaying ? Icons.ondemand_video : Icons.play_circle_fill,
            color: Colors.white.withValues(alpha: 0.92),
            size: 64,
          ),
          const SizedBox(height: 10),
          Text(
            strings.interactivePreviewSurface,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: Colors.white),
          ),
        ],
      ),
    );
  }
}

enum _PlayerAction {
  togglePlayPause,
  seekBack,
  seekForward,
  toggleFullscreen,
  exitFullscreen,
}

class _PlayerIntent extends Intent {
  const _PlayerIntent(this.action);

  final _PlayerAction action;
}
