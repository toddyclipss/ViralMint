import { useState } from "react"
import { Box, Typography, Button, Stack, TextField, IconButton } from "@mui/material"
import { IconUpload, IconX, IconLink } from "@tabler/icons-react"
import http from "../../api/http"

export default function ImageUpload({ label, value, onChange, onRemove }) {
  const [urlMode, setUrlMode] = useState(false)
  const [urlInput, setUrlInput] = useState("")
  const [uploading, setUploading] = useState(false)

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ""
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append("file", file)
      const res = await http.post("/api/media/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      onChange(res.data.url)
    } catch {
      onChange(null)
    } finally {
      setUploading(false)
    }
  }

  const handleUrlSubmit = () => {
    if (urlInput.trim()) {
      onChange(urlInput.trim())
      setUrlInput("")
      setUrlMode(false)
    }
  }

  if (value) {
    return (
      <Box>
        <Typography variant="caption" sx={{ fontWeight: 600, color: "text.secondary", mb: 0.5, display: "block" }}>
          {label}
        </Typography>
        <Box sx={{ position: "relative", display: "inline-block" }}>
          <Box
            component="img"
            src={value}
            alt={label}
            sx={{
              width: "100%", maxWidth: 200, height: 140, objectFit: "cover",
              borderRadius: "14px", border: 1, borderColor: "divider",
            }}
          />
          <IconButton
            size="small"
            onClick={onRemove}
            sx={{
              position: "absolute", top: 4, right: 4,
              bgcolor: "rgba(0,0,0,0.6)", color: "#fff",
              "&:hover": { bgcolor: "rgba(0,0,0,0.8)" },
              width: 24, height: 24, borderRadius: "8px",
            }}
          >
            <IconX size={14} stroke={1.8} />
          </IconButton>
        </Box>
        <Button size="small" onClick={onRemove} sx={{ mt: 0.5, borderRadius: "20px" }}>
          Remove & re-upload
        </Button>
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="caption" sx={{ fontWeight: 600, color: "text.secondary", mb: 0.5, display: "block" }}>
        {label}
      </Typography>
      {urlMode ? (
        <Stack direction="row" spacing={1} alignItems="center">
          <TextField
            size="small" fullWidth
            placeholder="https://example.com/image.png"
            value={urlInput}
            onChange={e => setUrlInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleUrlSubmit()}
          />
          <Button size="small" variant="contained" onClick={handleUrlSubmit} disabled={!urlInput.trim()} sx={{ borderRadius: "20px" }}>
            Add
          </Button>
          <Button size="small" variant="outlined" onClick={() => setUrlMode(false)} sx={{ borderRadius: "20px" }}>
            Cancel
          </Button>
        </Stack>
      ) : (
        <Stack direction="row" spacing={1} alignItems="center">
          <Button
            size="small" variant="outlined"
            startIcon={<IconUpload size={16} stroke={1.8} />}
            component="label"
            disabled={uploading}
            sx={{ borderRadius: "20px" }}
          >
            {uploading ? "Uploading..." : "Upload"}
            <input type="file" hidden accept="image/*" onChange={handleFile} />
          </Button>
          <Button size="small" variant="outlined" startIcon={<IconLink size={16} stroke={1.8} />} onClick={() => setUrlMode(true)} sx={{ borderRadius: "20px" }}>
            Paste URL
          </Button>
        </Stack>
      )}
    </Box>
  )
}
