import 'package:flutter/material.dart';

import '../app_localization.dart';

enum VideoFitMode { contain, cover }

extension VideoFitModePresentation on VideoFitMode {
  BoxFit get boxFit => switch (this) {
        VideoFitMode.contain => BoxFit.contain,
        VideoFitMode.cover => BoxFit.cover,
      };

  String get keyValue => switch (this) {
        VideoFitMode.contain => 'contain',
        VideoFitMode.cover => 'cover',
      };

  IconData get icon => switch (this) {
        VideoFitMode.contain => Icons.zoom_out_map,
        VideoFitMode.cover => Icons.zoom_in_map,
      };

  VideoFitMode get toggled => switch (this) {
        VideoFitMode.contain => VideoFitMode.cover,
        VideoFitMode.cover => VideoFitMode.contain,
      };
}

String formatVideoTimestamp(Duration duration) {
  final minutes = duration.inMinutes.remainder(60).toString().padLeft(2, '0');
  final seconds = duration.inSeconds.remainder(60).toString().padLeft(2, '0');
  if (duration.inHours > 0) {
    final hours = duration.inHours.toString().padLeft(2, '0');
    return '$hours:$minutes:$seconds';
  }
  return '$minutes:$seconds';
}

class LessonVideoViewport extends StatelessWidget {
  const LessonVideoViewport({
    super.key,
    required this.child,
    required this.aspectRatio,
    required this.fitMode,
    required this.fullscreen,
  });

  final Widget child;
  final double aspectRatio;
  final VideoFitMode fitMode;
  final bool fullscreen;

  @override
  Widget build(BuildContext context) {
    final safeAspectRatio = aspectRatio <= 0 ? 16 / 9 : aspectRatio;
    final scaledSurface = SizedBox(
      width: safeAspectRatio * 1000,
      height: 1000,
      child: child,
    );

    if (!fullscreen) {
      return LayoutBuilder(
        builder: (context, constraints) {
          final viewportWidth =
              constraints.maxWidth.isFinite && constraints.maxWidth > 0
                  ? constraints.maxWidth
                  : MediaQuery.sizeOf(context).width;
          final preferredHeight = viewportWidth / safeAspectRatio;
          final clampedHeight = preferredHeight.clamp(220.0, 320.0);
          return ClipRRect(
            borderRadius: BorderRadius.circular(18),
            child: SizedBox(
              width: double.infinity,
              height: clampedHeight,
              child: ColoredBox(
                color: Colors.black,
                child: FittedBox(
                  key: ValueKey('video-fit-${fitMode.keyValue}'),
                  fit: fitMode.boxFit,
                  child: scaledSurface,
                ),
              ),
            ),
          );
        },
      );
    }

    return ColoredBox(
      color: Colors.black,
      child: SizedBox.expand(
        child: FittedBox(
          key: ValueKey('video-fit-${fitMode.keyValue}'),
          fit: fitMode.boxFit,
          clipBehavior: Clip.hardEdge,
          child: scaledSurface,
        ),
      ),
    );
  }
}

class LessonVideoFrame extends StatelessWidget {
  const LessonVideoFrame({
    super.key,
    required this.title,
    required this.surface,
    required this.position,
    required this.duration,
    required this.isPlaying,
    required this.controlsVisible,
    required this.fullscreen,
    required this.fitMode,
    required this.onSurfaceTap,
    required this.onPlayPause,
    required this.onReplay10,
    required this.onForward10,
    required this.onSeek,
    this.zoomLabel,
    this.isZoomed = false,
    this.onResetZoom,
    this.onToggleFullscreen,
    this.onToggleFitMode,
    this.onSurfaceDoubleTap,
    this.onSurfaceDoubleTapDown,
  });

  final String title;
  final Widget surface;
  final Duration position;
  final Duration duration;
  final bool isPlaying;
  final bool controlsVisible;
  final bool fullscreen;
  final VideoFitMode fitMode;
  final VoidCallback onSurfaceTap;
  final VoidCallback onPlayPause;
  final VoidCallback onReplay10;
  final VoidCallback onForward10;
  final ValueChanged<double> onSeek;
  final String? zoomLabel;
  final bool isZoomed;
  final VoidCallback? onResetZoom;
  final VoidCallback? onToggleFullscreen;
  final VoidCallback? onToggleFitMode;
  final VoidCallback? onSurfaceDoubleTap;
  final GestureTapDownCallback? onSurfaceDoubleTapDown;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final strings = context.strings;
    final safeDuration = duration < Duration.zero ? Duration.zero : duration;
    final clampedPosition = position > safeDuration ? safeDuration : position;
    final maxSeconds = safeDuration.inMilliseconds <= 0
        ? 1.0
        : safeDuration.inMilliseconds.toDouble();
    final sliderValue =
        clampedPosition.inMilliseconds.clamp(0, maxSeconds.toInt()).toDouble();
    final labelStyle = theme.textTheme.bodySmall
        ?.copyWith(color: Colors.white.withValues(alpha: 0.92));

    final titleRow = Row(
      children: [
        Expanded(
          child: Text(
            title,
            key: const ValueKey('video-title-overlay'),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.titleMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        if (fullscreen && onToggleFitMode != null)
          IconButton(
            key: const ValueKey('fit-toggle-button'),
            tooltip: fitMode == VideoFitMode.contain
                ? strings.zoomToFill
                : strings.fitInsideScreen,
            onPressed: onToggleFitMode,
            icon: Icon(fitMode.icon, color: Colors.white),
          ),
        if (fullscreen && isZoomed && zoomLabel != null) ...[
          Container(
            key: const ValueKey('video-zoom-label'),
            margin: const EdgeInsets.only(right: 4),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.44),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              zoomLabel!,
              style: theme.textTheme.labelMedium?.copyWith(color: Colors.white),
            ),
          ),
          IconButton(
            key: const ValueKey('reset-zoom-button'),
            tooltip: strings.resetZoom,
            onPressed: onResetZoom,
            icon: const Icon(Icons.center_focus_strong, color: Colors.white),
          ),
        ],
        if (onToggleFullscreen != null)
          IconButton(
            key: ValueKey(
              fullscreen ? 'exit-fullscreen-button' : 'enter-fullscreen-button',
            ),
            tooltip:
                fullscreen ? strings.exitFullscreen : strings.openFullscreen,
            onPressed: onToggleFullscreen,
            icon: Icon(
              fullscreen ? Icons.fullscreen_exit : Icons.fullscreen,
              color: Colors.white,
            ),
          ),
      ],
    );

    final centerPlayButton = Center(
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.28),
          shape: BoxShape.circle,
        ),
        child: IconButton(
          key: const ValueKey('play-pause-button'),
          tooltip: isPlaying ? strings.pauseVideo : strings.playVideo,
          onPressed: onPlayPause,
          iconSize: fullscreen ? 72 : 58,
          color: Colors.white,
          icon: Icon(
            isPlaying ? Icons.pause_circle_filled : Icons.play_circle_fill,
          ),
        ),
      ),
    );

    final inlineOverlay = AnimatedOpacity(
      key: const ValueKey('video-overlay-opacity'),
      opacity: controlsVisible ? 1 : 0,
      duration: const Duration(milliseconds: 180),
      child: IgnorePointer(
        ignoring: !controlsVisible,
        child: Stack(
          children: [
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withValues(alpha: 0.72),
                      Colors.black.withValues(alpha: 0),
                    ],
                  ),
                ),
                child: SafeArea(
                  bottom: false,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 18),
                    child: titleRow,
                  ),
                ),
              ),
            ),
            Positioned.fill(child: centerPlayButton),
          ],
        ),
      ),
    );

    final fullscreenControls = AnimatedOpacity(
      key: const ValueKey('video-overlay-opacity'),
      opacity: controlsVisible ? 1 : 0,
      duration: const Duration(milliseconds: 180),
      child: IgnorePointer(
        ignoring: !controlsVisible,
        child: Stack(
          children: [
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withValues(alpha: 0.72),
                      Colors.black.withValues(alpha: 0),
                    ],
                  ),
                ),
                child: SafeArea(
                  bottom: false,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 18),
                    child: titleRow,
                  ),
                ),
              ),
            ),
            Positioned.fill(child: centerPlayButton),
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withValues(alpha: 0),
                      Colors.black.withValues(alpha: 0.84),
                    ],
                  ),
                ),
                child: SafeArea(
                  top: false,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 44, 12, 14),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SliderTheme(
                          data: SliderTheme.of(context).copyWith(
                            overlayShape: const RoundSliderOverlayShape(
                                overlayRadius: 12),
                            trackHeight: 3,
                          ),
                          child: Slider(
                            key: const ValueKey('video-progress-slider'),
                            min: 0,
                            max: maxSeconds,
                            value: sliderValue,
                            onChanged: onSeek,
                          ),
                        ),
                        Row(
                          children: [
                            IconButton(
                              key: const ValueKey('replay-10-button'),
                              tooltip: strings.replayTenSeconds,
                              onPressed: onReplay10,
                              color: Colors.white,
                              icon: const Icon(Icons.replay_10),
                            ),
                            IconButton(
                              key: const ValueKey('forward-10-button'),
                              tooltip: strings.skipForwardTenSeconds,
                              onPressed: onForward10,
                              color: Colors.white,
                              icon: const Icon(Icons.forward_10),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '${formatVideoTimestamp(clampedPosition)} / ${formatVideoTimestamp(safeDuration)}',
                                key: const ValueKey('video-time-label'),
                                style: labelStyle,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );

    if (fullscreen) {
      return Material(
        color: Colors.transparent,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Positioned.fill(
              child: GestureDetector(
                key: const ValueKey('video-surface'),
                behavior: HitTestBehavior.opaque,
                onTap: onSurfaceTap,
                onDoubleTap: onSurfaceDoubleTap,
                onDoubleTapDown: onSurfaceDoubleTapDown,
                child: surface,
              ),
            ),
            Positioned.fill(child: fullscreenControls),
          ],
        ),
      );
    }

    final inlineBottomBar = AnimatedOpacity(
      opacity: controlsVisible ? 1 : 0,
      duration: const Duration(milliseconds: 180),
      child: IgnorePointer(
        ignoring: !controlsVisible,
        child: Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest
                .withValues(alpha: 0.55),
            borderRadius: BorderRadius.circular(16),
          ),
          padding: const EdgeInsets.fromLTRB(10, 6, 10, 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SliderTheme(
                data: SliderTheme.of(context).copyWith(
                  overlayShape:
                      const RoundSliderOverlayShape(overlayRadius: 12),
                  trackHeight: 3,
                ),
                child: Slider(
                  key: const ValueKey('video-progress-slider'),
                  min: 0,
                  max: maxSeconds,
                  value: sliderValue,
                  onChanged: onSeek,
                ),
              ),
              Row(
                children: [
                  IconButton(
                    key: const ValueKey('replay-10-button'),
                    tooltip: strings.replayTenSeconds,
                    onPressed: onReplay10,
                    icon: const Icon(Icons.replay_10),
                  ),
                  IconButton(
                    key: const ValueKey('forward-10-button'),
                    tooltip: strings.skipForwardTenSeconds,
                    onPressed: onForward10,
                    icon: const Icon(Icons.forward_10),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${formatVideoTimestamp(clampedPosition)} / ${formatVideoTimestamp(safeDuration)}',
                      key: const ValueKey('video-time-label'),
                      style: theme.textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Material(
          color: Colors.transparent,
          child: Stack(
            children: [
              GestureDetector(
                key: const ValueKey('video-surface'),
                behavior: HitTestBehavior.opaque,
                onTap: onSurfaceTap,
                child: surface,
              ),
              Positioned.fill(child: inlineOverlay),
            ],
          ),
        ),
        const SizedBox(height: 10),
        inlineBottomBar,
      ],
    );
  }
}
