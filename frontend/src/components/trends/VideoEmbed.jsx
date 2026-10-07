// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (c) 2025-2026 ViralMint Contributors
import { useEffect, useState } from "react"
import { Box, Typography, IconButton, Stack } from "@mui/material"
import OpenInNewIcon from "@mui/icons-material/OpenInNew"
import PlayArrowIcon from "@mui/icons-material/PlayArrow"
import MovieOutlinedIcon from "@mui/icons-material/MovieOutlined"
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined"

function extractYouTubeId(url) {
  if (!url) return null
  try {
    const u = new URL(url)
    if (u.searchParams.get("v")) return u.searchParams.get("v")
    const parts = u.pathname.split("/").filter(Boolean)
    return parts.length ? parts[parts.length - 1] : null
  } catch { return null }
}

const VERTICAL_PLATFORMS = new Set(["tiktok", "douyin", "kuaishou", "instagram"])

/** Portrait (9:16) for short-form hosts and YouTube Shorts; 16:9 otherwise. */
export function isVertical(platform, videoUrl) {
  if (VERTICAL_PLATFORMS.has(platform)) return true
  return platform === "youtube" && /\/shorts\//.test(videoUrl || "")
}

export function previewCandidates({ platform, videoUrl, videoId, thumbnailUrl }) {
  if (platform === "youtube") {
    const id = extractYouTubeId(videoUrl) || videoId
    if (id) return [`https://i.ytimg.com/vi/${id}/maxresdefault.jpg`, `https://i.ytimg.com/vi/${id}/hqdefault.jpg`]
  }
  return thumbnailUrl ? [thumbnailUrl] : []
}

export default function VideoEmbed({ platform, videoId, videoUrl, thumbnailUrl }) {
  const candidates = previewCandidates({ platform, videoUrl, videoId, thumbnailUrl })
  const [idx, setIdx] = useState(0)
  useEffect(() => { setIdx(0) }, [platform, videoUrl, videoId, thumbnailUrl])

  const vertical = isVertical(platform, videoUrl)
  const src = candidates[idx]
  const isNews = platform === "news"
  const openUrl = videoUrl || (platform === "youtube" && videoId ? `https://www.youtube.com/watch?v=${videoId}` : null)
  if (!src && !openUrl) return null

  const next = () => setIdx((i) => i + 1)
  const open = () => { if (openUrl) window.open(openUrl, "_blank", "noopener") }

  return (
    <Box
      data-testid="trend-preview"
      data-orientation={vertical ? "portrait" : "landscape"}
      role={openUrl ? "link" : undefined}
      tabIndex={openUrl ? 0 : undefined}
      aria-label={openUrl ? (isNews ? "Open the article" : "Watch on the original platform") : undefined}
      onClick={open}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open() } }}
      sx={{
        position: "relative",
        ...(!src
          ? { width: "100%", height: 140 }
          : vertical
            ? { height: "min(480px, 58vh)", aspectRatio: "9 / 16", mx: "auto", maxWidth: "100%" }
            : { width: "100%", aspectRatio: "16 / 9" }),
        borderRadius: 1.5,
        overflow: "hidden",
        cursor: openUrl ? "pointer" : "default",
        bgcolor: "grey.900",
        "&:hover .play-overlay, &:focus-visible .play-overlay": { opacity: 1 },
      }}
    >
      {src ? (
        <Box
          component="img"
          key={src}
          src={src}
          alt=""
          referrerPolicy="no-referrer"
          decoding="async"
          onError={next}
          onLoad={(e) => { if (platform === "youtube" && e.currentTarget.naturalWidth <= 120) next() }}
          sx={{ width: "100%", height: "100%", display: "block",
                objectFit: platform === "youtube" ? "cover" : "contain" }}
        />
      ) : (
        <Stack alignItems="center" justifyContent="center" spacing={0.75}
          sx={{ position: "absolute", inset: 0, color: "grey.400", px: 2, textAlign: "center" }}>
          {isNews ? <ArticleOutlinedIcon sx={{ fontSize: 36 }} /> : <MovieOutlinedIcon sx={{ fontSize: 36 }} />}
          <Typography variant="caption" sx={{ color: "grey.400" }}>
            {candidates.length ? "Preview no longer available" : "No preview"}
            {openUrl ? " — open the original to watch" : ""}
          </Typography>
        </Stack>
      )}
      {openUrl && !isNews && (
        <Box
          className="play-overlay"
          sx={{
            position: "absolute", inset: 0, pointerEvents: "none",
            display: "flex", alignItems: "center", justifyContent: "center",
            bgcolor: "rgba(0,0,0,0.35)", opacity: 0, transition: "opacity 0.2s",
          }}
        >
          <PlayArrowIcon sx={{ fontSize: 56, color: "common.white" }} />
        </Box>
      )}
      {openUrl && (
        <IconButton
          aria-label={isNews ? "Open the article in a new tab" : "Watch on the original platform"}
          size="small"
          tabIndex={-1}
          sx={{
            position: "absolute", top: 6, right: 6,
            bgcolor: "rgba(0,0,0,0.6)", color: "common.white",
            "&:hover": { bgcolor: "rgba(0,0,0,0.8)" },
          }}
          onClick={(e) => { e.stopPropagation(); open() }}
        >
          <OpenInNewIcon sx={{ fontSize: 16 }} />
        </IconButton>
      )}
    </Box>
  )
}
