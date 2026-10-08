import { useState } from "react"
import { Box, Typography, Button, TextField, Stack, Link } from "@mui/material"
import { IconExternalLink } from "@tabler/icons-react"

export default function WizardStep({ step, onComplete }) {
  const [inputValue, setInputValue] = useState("")

  if (!step) return null

  const handleSubmit = () => {
    if (inputValue.trim()) {
      onComplete(step.id, inputValue.trim(), step.field)
      setInputValue("")
    }
  }

  return (
    <Box sx={{ py: 2 }}>
      <Typography sx={{ mb: 2, lineHeight: 1.6 }}>{step.instruction}</Typography>

      {step.action === "open_url" && (
        <Stack spacing={1.5}>
          <Link href={step.url} target="_blank" rel="noopener noreferrer" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            Open in browser <IconExternalLink size={14} stroke={1.8} />
          </Link>
          <Button variant="contained" onClick={() => onComplete(step.id, true)} sx={{ alignSelf: "flex-start", borderRadius: "20px" }}>
            Continue
          </Button>
        </Stack>
      )}

      {step.action === "wait_confirm" && (
        <Button variant="contained" onClick={() => onComplete(step.id, true)} sx={{ borderRadius: "20px" }}>
          {step.confirm_label || "Continue"}
        </Button>
      )}

      {step.action === "text_input" && (
        <Box sx={{ display: "flex", gap: 1 }}>
          <TextField
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={step.placeholder || ""}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            size="small"
            fullWidth
            sx={{ "& .MuiOutlinedInput-root": { bgcolor: "background.default", borderRadius: "12px" } }}
          />
          <Button variant="contained" onClick={handleSubmit} disabled={!inputValue.trim()} sx={{ borderRadius: "20px" }}>
            Save
          </Button>
        </Box>
      )}

      {step.action === "oauth_button" && (
        <Button variant="contained" component="a" href={step.endpoint} target="_blank" rel="noopener noreferrer" sx={{ borderRadius: "20px" }}>
          {step.button_label || "Connect"}
        </Button>
      )}

      {step.action === "select" && step.options && (
        <Stack spacing={1}>
          {step.options.map((opt) => (
            <Button
              key={opt.value}
              variant="outlined"
              onClick={() => onComplete(step.id, opt.value, step.field)}
              sx={{ justifyContent: "flex-start", borderColor: "divider", color: "text.primary", borderRadius: "12px" }}
            >
              {opt.label}
            </Button>
          ))}
        </Stack>
      )}

      {step.action === "link_guide" && step.links && (
        <Stack spacing={1}>
          {Object.entries(step.links).map(([key, link]) => (
            <Link key={key} href={link.url} target="_blank" rel="noopener noreferrer" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {link.label} <IconExternalLink size={14} stroke={1.8} />
            </Link>
          ))}
          <Button variant="contained" onClick={() => onComplete(step.id, true)} sx={{ alignSelf: "flex-start", mt: 1, borderRadius: "20px" }}>
            I have my API key
          </Button>
        </Stack>
      )}

      {step.action === "success" && (
        <Typography sx={{ color: "primary.main", fontWeight: 600 }}>{step.instruction}</Typography>
      )}
    </Box>
  )
}
