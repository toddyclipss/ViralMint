import { Typography } from "@mui/material"
import { IconAspectRatio } from "@tabler/icons-react"
import ToolRunner from "../../components/tools/ToolRunner"
import useDocumentTitle from "../../hooks/useDocumentTitle"

export default function ToolReframe() {
  useDocumentTitle("Reframe to Vertical")
  return (
    <ToolRunner
      title="Reframe to Vertical"
      description="Convert 16:9 landscape to 9:16 with face-tracking"
      icon={<IconAspectRatio size={28} stroke={1.8} />}
      endpoint="/api/tools/reframe"
    >
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Fits the whole frame into 9:16 over a blurred, zoomed copy of itself —
        nothing is cropped away. Sources that are already 9:16 or narrower are
        returned unchanged; square and 4:5 clips are reframed.
      </Typography>
    </ToolRunner>
  )
}
