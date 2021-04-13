# steps to run before importing django

# patch this here because we have to make sure we do it before any file imports the eyecite library
import scripts.patch_reporters_db  # noqa
