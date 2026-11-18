# GTA VI Instagram page kit

Original, graphics-only content for a GTA VI fan page: 4 posters, 1 carousel, 1 Reel (Indian-English voice-over + beat), captions, hashtags.
The look is an original retro "vice sunset" HUD style made by code. No Rockstar art, logo, trailer frames or characters are used (Meta takedown + copyright risk).

## Setup (once)
    pip install -r requirements.txt
    set GEMINI_API_KEY=your_key        (Windows; optional. Without it the offline template copy + Edge voice are used)
Edit `config.json` (handle, page name, tone) and keep `facts.json` updated with CONFIRMED facts + source links only.

## Make a pack
    python make.py                      # new pack in output/pack_<seed>
    python make.py --offline            # no AI, template copy
    python make.py --voice edge         # free voice (more robotic); auto = ElevenLabs > Sarvam > Gemini > Edge
    python make.py --no-reel --palette teal
Palettes: sunset, teal dusk, purple hr, hot red, lime neon, ocean (see kit/style.py).

## Rules the generator follows
Only facts from `facts.json` are written as facts. No rumours, no income promises, fan-page disclaimer on every image.
Always read captions_and_hashtags.txt and verify facts before posting. See POSTING_CHEATSHEET.md.
