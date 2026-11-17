# G.O.A.T. slide images (user drop-in)

The original Fallout 3 slide images shown during the G.O.A.T. are copyrighted and are
**not shipped** with this integration. If you own the game, drop your own copies here:

```
custom_components/gamified_gtd/www/gamified_gtd_icons/goat/slide_1.png
...
custom_components/gamified_gtd/www/gamified_gtd_icons/goat/slide_10.png
```

They are served at `/gamified_gtd_static/gamified_gtd_icons/goat/slide_<n>.png` and are
shown:

- on the `custom:gamified-gtd-goat` dashboard card (one slide per question), and
- in the G.O.A.T. step of the options flow (markdown description) — but only for slides
  whose file actually exists, so no broken images are shown.

Without the files, the G.O.A.T. works fine with text only (questions + answers).
