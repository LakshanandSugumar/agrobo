// The brand film shown on the homepage. To swap in a new cut, replace the files in
// public/film/ (keep the names) or point these paths at the new ones.
export const FILM = {
  // H.264 first (Safari, Chrome, Edge), VP9 fallback (browsers without H.264)
  sources: [
    { src: "/film/agrobo-film.mp4", type: "video/mp4" },
    { src: "/film/agrobo-film.webm", type: "video/webm" },
  ],
  poster: "/film/agrobo-film-poster.jpg",
  durationLabel: "1:26",
  /** idle time at the top of the homepage before the film takes over */
  idleMs: 4000,
};

export const PLAY_FILM_EVENT = "agrobo:play-film";
