import praw

reddit = praw.Reddit(
    client_id = "SXtk1VW7Lw90s7AxtAO4yA",
    client_secret = "rp6k-MH3NOjJWC3RgY16WLi3RhPUbg",
    user_agent = "macOS:my172Crawler:1.0 (by /u/flurfsky)",
    # since there are multiple users of this app, skip username/password, give crawler "read only" privilege
    # username = "YOUR_USERNAME",
    # password = "YOUR_PASSWORD"
)