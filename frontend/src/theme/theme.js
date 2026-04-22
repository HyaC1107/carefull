import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      light: '#4b617f',
      main: '#1E3A5F',
      dark: '#152842',
      contrastText: '#ffffff',
    },
    secondary: {
      light: '#6ea6e7',
      main: '#4A90E2',
      dark: '#33649e',
      contrastText: '#ffffff',
    },
    text: {
      primary: '#1D293D',
      secondary: '#6B7C93',
    },
    background: {
      default: '#E5E7EB',
      paper: '#FFFFFF',
    },
  },
});

export default theme;