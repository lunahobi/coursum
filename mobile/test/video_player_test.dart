import 'package:coursum_mobile/player/lesson_video_player.dart';
import 'package:coursum_mobile/player/video_player_overlays.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> configureViewport(WidgetTester tester) async {
  tester.view.physicalSize = const Size(1440, 2600);
  tester.view.devicePixelRatio = 1;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

Future<void> doubleTapFullscreenSurface(WidgetTester tester) async {
  final surface = find.byKey(const ValueKey('video-surface')).first;
  final rect = tester.getRect(surface);
  final point = Offset(rect.right - 72, rect.top + rect.height * 0.28);
  await tester.tapAt(point);
  await tester.pump(const Duration(milliseconds: 80));
  await tester.tapAt(point);
}

void main() {
  testWidgets('video frame shows an explicit resume action', (tester) async {
    var resumeTapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LessonVideoFrame(
            title: 'Lesson video',
            surface: const SizedBox(width: 320, height: 180),
            position: Duration.zero,
            duration: const Duration(minutes: 8),
            isPlaying: false,
            controlsVisible: true,
            fullscreen: false,
            fitMode: VideoFitMode.contain,
            resumePosition: const Duration(minutes: 3, seconds: 12),
            onResumeFromPosition: () => resumeTapped = true,
            onSurfaceTap: () {},
            onPlayPause: () {},
            onReplay10: () {},
            onForward10: () {},
            onSeek: (_) {},
          ),
        ),
      ),
    );

    await tester
        .tap(find.byKey(const ValueKey('resume-video-position-button')));
    await tester.pump();

    expect(resumeTapped, isTrue);
  });

  testWidgets('video frame shows buffering feedback over the video',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LessonVideoFrame(
            title: 'Lesson video',
            surface: const SizedBox(width: 320, height: 180),
            position: Duration.zero,
            duration: const Duration(minutes: 8),
            isPlaying: true,
            controlsVisible: false,
            buffering: true,
            fullscreen: false,
            fitMode: VideoFitMode.contain,
            onSurfaceTap: () {},
            onPlayPause: () {},
            onReplay10: () {},
            onForward10: () {},
            onSeek: (_) {},
          ),
        ),
      ),
    );

    expect(find.byKey(const ValueKey('video-buffering-indicator')),
        findsOneWidget);
  });

  testWidgets('fullscreen video only pans after zooming', (tester) async {
    await configureViewport(tester);
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: InlineVideoPanel(
            url: 'https://cdn.example.com/lesson.mp4',
            title: 'Lesson video',
            previewMode: InlineVideoPreviewMode.embedded,
          ),
        ),
      ),
    );

    await tester.tap(find.byKey(const ValueKey('enter-fullscreen-button')));
    await tester.pumpAndSettle();

    var viewer = tester.widget<InteractiveViewer>(
      find.byKey(const ValueKey('fullscreen-zoom-surface')),
    );
    expect(viewer.panEnabled, isFalse);
    expect(viewer.boundaryMargin, EdgeInsets.zero);

    await doubleTapFullscreenSurface(tester);
    await tester.pumpAndSettle();

    viewer = tester.widget<InteractiveViewer>(
      find.byKey(const ValueKey('fullscreen-zoom-surface')),
    );
    expect(viewer.panEnabled, isTrue);
    expect(viewer.boundaryMargin, const EdgeInsets.all(120));
  });
}
