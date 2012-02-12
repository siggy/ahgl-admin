#!/usr/bin/env python
import os
import contextlib
import ahgl_admin

DATA_DIR = './data'
SEASON = '2'

if __name__ == '__main__':
  if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    with contextlib.closing(ahgl_admin.open_db(os.path.join(DATA_DIR, "ahgl.sq3")).cursor()) as cursor:
      for filename in ['./schema.sql', './test_data.sql', './test_lineup.sql', './test_results.sql']:
        with ahgl_admin.app.open_resource(filename) as f:
          cursor.executescript(f.read())

  ahgl_admin.app.config.from_object(__name__)
  ahgl_admin.app.secret_key = 'AHGL'
  ahgl_admin.app.run(debug=True)
