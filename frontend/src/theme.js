import { createTheme, alpha } from "@mui/material/styles"

// ── Shadow system ────────────────────────────────────────────────────────────
const shadows = {
  sm: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
  md: "0 4px 14px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.03)",
  lg: "0 12px 28px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.04)",
  xl: "0 20px 40px rgba(0,0,0,0.1), 0 8px 16px rgba(0,0,0,0.05)",
  glow: "0 0 20px rgba(139,92,246,0.18)",
  glowStrong: "0 0 28px rgba(139,92,246,0.32)",
  up: "0 -2px 8px rgba(0,0,0,0.04)",
}

const darkShadows = {
  sm: "0 1px 3px rgba(0,0,0,0.2), 0 1px 2px rgba(0,0,0,0.12)",
  md: "0 4px 14px rgba(0,0,0,0.25), 0 2px 6px rgba(0,0,0,0.15)",
  lg: "0 12px 28px rgba(0,0,0,0.35), 0 4px 10px rgba(0,0,0,0.2)",
  xl: "0 20px 40px rgba(0,0,0,0.45), 0 8px 16px rgba(0,0,0,0.25)",
  glow: "0 0 20px rgba(139,92,246,0.25)",
  glowStrong: "0 0 28px rgba(139,92,246,0.40)",
  up: "0 -2px 8px rgba(0,0,0,0.15)",
}

export default function createAppTheme(mode) {
  const isDark = mode === "dark"
  const s = isDark ? darkShadows : shadows
  const P = "#8b5cf6" // Refined soft purple / electric lilac

  const theme = createTheme({
    palette: {
      mode,
      primary: { main: P, light: "#a78bfa", dark: "#7c3aed", contrastText: "#fff" },
      secondary: { main: isDark ? "#c4b5fd" : "#8b5cf6" },
      background: {
        default: isDark ? "#0f0d15" : "#f8f7fc",
        paper: isDark ? "#171522" : "#ffffff",
        subtle: isDark ? "#1d1a2c" : "#f3f0fb",
      },
      text: {
        primary: isDark ? "#f3f0fb" : "#1e1b2e",
        secondary: isDark ? "#a7a1be" : "#6c6684",
      },
      success: { main: "#10b981" },
      warning: { main: "#f59e0b" },
      error: { main: "#ef4444" },
      info: { main: "#6366f1" },
      divider: isDark ? "rgba(255,255,255,0.08)" : "rgba(139,92,246,0.08)",
      action: {
        hover: isDark ? "rgba(255,255,255,0.05)" : "rgba(139,92,246,0.04)",
        selected: "rgba(139,92,246,0.12)",
      },
    },
    typography: {
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      h4: { fontWeight: 700, fontSize: "1.5rem", letterSpacing: "-0.02em" },
      h5: { fontWeight: 700, fontSize: "1.15rem", letterSpacing: "-0.01em" },
      h6: { fontWeight: 600, fontSize: "1rem" },
      subtitle1: { fontWeight: 500 },
      subtitle2: { fontWeight: 600 },
      body1: { lineHeight: 1.65 },
      body2: { lineHeight: 1.6 },
      button: { fontWeight: 600 },
    },
    shape: { borderRadius: 12 },
    customShadows: s,
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: isDark ? "#0f0d15" : "#f8f7fc",
            colorScheme: mode,
          },
          // Smoother scrollbars
          "*::-webkit-scrollbar": { width: 6 },
          "*::-webkit-scrollbar-track": { background: "transparent" },
          "*::-webkit-scrollbar-thumb": {
            background: isDark ? "rgba(255,255,255,0.1)" : "rgba(139,92,246,0.12)",
            borderRadius: 3,
          },
          "*::-webkit-scrollbar-thumb:hover": {
            background: isDark ? "rgba(139,92,246,0.25)" : "rgba(139,92,246,0.25)",
          },
          // Accessibility — a visible focus ring on keyboard-focused
          // interactive elements. MUI's ButtonBase resets `outline: 0` and
          // relies on a faint focus ripple, which many surfaces here hide, so
          // Tab left no visible trace. :focus-visible keeps mouse clicks from
          // drawing it. Components with a bespoke focus style still win on
          // specificity.
          "a:focus-visible, button:focus-visible, [role='button']:focus-visible, [tabindex]:focus-visible": {
            outline: `2px solid ${alpha(P, isDark ? 0.9 : 0.8)}`,
            outlineOffset: 2,
            borderRadius: 12,
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 600,
            fontSize: "0.85rem",
            borderRadius: 20,
            boxShadow: "none",
            padding: "6px 18px",
            transition: "all 0.15s ease",
            "&:hover": {
              boxShadow: "none",
              transform: "translateY(-1px)",
            },
            "&:active": {
              transform: "translateY(0)",
            },
          },
          sizeSmall: {
            fontSize: "0.8rem",
            padding: "4px 14px",
            borderRadius: 16,
          },
          contained: {
            boxShadow: s.sm,
            "&:hover": { boxShadow: s.md },
          },
          containedPrimary: {
            background: `linear-gradient(135deg, ${P}, #a78bfa)`,
            // The gradient is a background-IMAGE, so MUI's disabled colour
            // never showed through: a disabled primary button looked enabled
            // on every page.
            "&.Mui-disabled": {
              background: isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.12)",
              color: isDark ? "rgba(255,255,255,0.38)" : "rgba(0,0,0,0.38)",
              boxShadow: "none",
            },
            "&:hover": {
              background: `linear-gradient(135deg, #7c3aed, #9d72ff)`,
              boxShadow: `${s.md}, ${s.glow}`,
            },
          },
          outlined: {
            borderColor: isDark ? "rgba(255,255,255,0.12)" : "rgba(139,92,246,0.15)",
            "&:hover": {
              borderColor: P,
              backgroundColor: `rgba(139,92,246,0.06)`,
            },
          },
          text: {
            padding: "4px 12px",
            "&:hover": {
              backgroundColor: `rgba(139,92,246,0.08)`,
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
          elevation1: { boxShadow: s.sm },
          elevation2: { boxShadow: s.md },
          elevation4: { boxShadow: s.lg },
          elevation8: { boxShadow: s.xl },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: isDark ? "rgba(15,13,21,0.92)" : "rgba(255,255,255,0.88)",
            backdropFilter: "blur(20px) saturate(1.4)",
            WebkitBackdropFilter: "blur(20px) saturate(1.4)",
            borderRight: `1px solid ${isDark ? "rgba(255,255,255,0.06)" : "rgba(139,92,246,0.08)"}`,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            border: `1px solid ${isDark ? "rgba(255,255,255,0.07)" : "rgba(139,92,246,0.09)"}`,
            borderRadius: 16,
            boxShadow: s.sm,
            transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
            "&:hover": {
              boxShadow: `${s.lg}, ${s.glow}`,
              borderColor: isDark ? "rgba(139,92,246,0.35)" : "rgba(139,92,246,0.30)",
              transform: "translateY(-2px)",
            },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 600, borderRadius: 16 },
          filledSuccess: { backgroundColor: "#12883e" },
          outlined: {
            borderColor: isDark ? "rgba(255,255,255,0.12)" : "rgba(139,92,246,0.15)",
            transition: "all 0.15s ease",
            "&:hover": {
              borderColor: P,
              backgroundColor: "rgba(139,92,246,0.08)",
            },
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            "& .MuiOutlinedInput-root": {
              borderRadius: 14,
              transition: "all 0.15s ease",
              "& fieldset": {
                borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(139,92,246,0.15)",
                transition: "all 0.15s ease",
              },
              "&:hover fieldset": {
                borderColor: isDark ? "rgba(139,92,246,0.4)" : "rgba(139,92,246,0.35)",
              },
              "&.Mui-focused": {
                backgroundColor: isDark ? "rgba(139,92,246,0.04)" : "rgba(139,92,246,0.02)",
              },
              "&.Mui-focused fieldset": {
                borderColor: P,
                borderWidth: 2,
              },
            },
          },
        },
      },
      MuiSelect: {
        styleOverrides: {
          root: { borderRadius: 14 },
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            borderRadius: 22,
            boxShadow: isDark ? "0 12px 40px rgba(0,0,0,0.7)" : "0 12px 40px rgba(139,92,246,0.15)",
            border: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "rgba(139,92,246,0.12)"}`,
          },
          backdrop: {
            backdropFilter: "blur(8px)",
            WebkitBackdropFilter: "blur(8px)",
            backgroundColor: isDark ? "rgba(0,0,0,0.6)" : "rgba(15,13,21,0.3)",
          },
        },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: { borderRadius: 4, height: 6 },
          bar: { borderRadius: 4 },
        },
      },
      MuiSwitch: {
        styleOverrides: {
          switchBase: {
            "&.Mui-checked": { color: P },
            "&.Mui-checked + .MuiSwitch-track": { backgroundColor: P },
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 14,
            transition: "all 0.15s ease",
            "&.Mui-selected": {
              backgroundColor: "rgba(139,92,246,0.12)",
              "&:hover": { backgroundColor: "rgba(139,92,246,0.18)" },
            },
          },
        },
      },
      MuiTabs: {
        styleOverrides: {
          root: { minHeight: 40 },
          indicator: {
            backgroundColor: P,
            borderRadius: 3,
            height: 3,
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 500,
            fontSize: "0.9rem",
            minHeight: 40,
            padding: "8px 16px",
            borderRadius: "14px 14px 0 0",
            transition: "all 0.15s ease",
            "&.Mui-selected": {
              color: P,
              fontWeight: 700,
              backgroundColor: isDark ? "rgba(139,92,246,0.1)" : "rgba(139,92,246,0.06)",
            },
          },
        },
      },
      // Segmented controls had NO theme entry, so every call site styled
      // itself and the same widget rendered several different ways on one
      // screen. Giving the component a home here is the same rule the caption
      // enum and the tool job-type map follow: one source, and a call site
      // that disagrees is now visibly disagreeing.
      MuiToggleButtonGroup: {
        styleOverrides: {
          root: { borderRadius: 20 },
          grouped: {
            borderRadius: 20,
            // MUI zeroes the inner corners of a group; restore them so the
            // ends stay rounded and the seams stay square.
            "&:not(:first-of-type)": { borderTopLeftRadius: 0, borderBottomLeftRadius: 0 },
            "&:not(:last-of-type)": { borderTopRightRadius: 0, borderBottomRightRadius: 0 },
          },
        },
      },
      MuiToggleButton: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 600,
            borderRadius: 20,
          },
        },
      },
      MuiDivider: {
        styleOverrides: {
          root: { borderColor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)" },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: {
            backgroundColor: isDark ? "rgba(23, 21, 34, 0.95)" : "rgba(30, 27, 46, 0.95)",
            backdropFilter: "blur(10px)",
            WebkitBackdropFilter: "blur(10px)",
            border: "1px solid rgba(139, 92, 246, 0.22)",
            color: "#f3f0fb",
            borderRadius: 10,
            fontSize: "0.8rem",
            padding: "6px 12px",
            boxShadow: s.lg,
          },
          arrow: {
            color: isDark ? "rgba(23, 21, 34, 0.95)" : "rgba(30, 27, 46, 0.95)",
          },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: { borderRadius: 12 },
          filledSuccess: { background: "linear-gradient(135deg, #16a34a, #22c55e)" },
          filledError: { background: "linear-gradient(135deg, #dc2626, #ef4444)" },
          filledWarning: { background: "linear-gradient(135deg, #d97706, #f59e0b)" },
          filledInfo: { background: "linear-gradient(135deg, #2563eb, #3b82f6)" },
        },
      },
      MuiSnackbar: {
        styleOverrides: {
          root: { "& .MuiPaper-root": { borderRadius: 12, boxShadow: s.xl } },
        },
      },
    },
  })

  return theme
}
