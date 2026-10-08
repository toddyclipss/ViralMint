import { useState } from "react"
import { Box, Typography, Chip, Stack, TablePagination } from "@mui/material"
import TrendsResults from "../trends/TrendsResults"

export default function TrendsTab({ jobs = [], results = [], total = 0, onFetchResults, page = 0, rowsPerPage = 50, onPageChange, onRowsPerPageChange }) {
  const [selectedJobId, setSelectedJobId] = useState(null)
  const trendJobs = jobs.filter(j => j.job_type === "trend" || j.job_type === "trends")
  const items = results || []
  const count = total || 0

  return (
    <Box>
      {trendJobs.length > 0 && (
        <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ mb: 2 }}>
          <Chip
            label="All Results"
            onClick={() => { setSelectedJobId(null); onFetchResults?.(null, 0, rowsPerPage) }}
            color={!selectedJobId ? "primary" : "default"}
            variant={!selectedJobId ? "filled" : "outlined"}
            size="small"
          />
          {trendJobs.slice(0, 8).map(j => (
            <Chip
              key={j.id}
              label={`${j.created_at ? new Date(j.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : j.id.slice(0, 8)}${j.status === "success" ? " ✓" : j.status === "failed" ? " ✗" : ""}`}
              onClick={() => { setSelectedJobId(j.id); onFetchResults?.(j.id, 0, rowsPerPage) }}
              color={selectedJobId === j.id ? "primary" : "default"}
              variant={selectedJobId === j.id ? "filled" : "outlined"}
              size="small"
            />
          ))}
        </Stack>
      )}

      {items.length > 0 ? (
        <>
          <TrendsResults results={items}
            onRefresh={() => onFetchResults?.(selectedJobId, page * rowsPerPage, rowsPerPage)} />
          <TablePagination
            component="div"
            count={count}
            page={page}
            onPageChange={(e, p) => onPageChange?.(e, p, selectedJobId)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => onRowsPerPageChange?.(e, selectedJobId)}
            rowsPerPageOptions={[20, 50, 100]}
            sx={{ borderTop: 1, borderColor: "divider", mt: 1 }}
          />
        </>
      ) : (
        <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
          <Typography variant="h6" sx={{ mb: 0.5 }}>No trends yet</Typography>
          <Typography variant="body2">Ask the chat assistant to find trending videos for your niche.</Typography>
        </Box>
      )}
    </Box>
  )
}
