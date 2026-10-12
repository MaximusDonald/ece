import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        sovereign: {
          50: '#E8F1FA',
          100: '#D0E3F5',
          200: '#A1C7EB',
          300: '#72ABE1',
          400: '#438FD7',
          500: '#0052A5',
          600: '#003D7A',
          700: '#002E5D',
          800: '#001E40',
          900: '#000F23',
        },
        success: {
          50: '#E8F5ED',
          100: '#D1EBDC',
          200: '#A3D7B9',
          300: '#75C396',
          400: '#47AF73',
          500: '#007B3F',
          600: '#006233',
          700: '#004926',
          800: '#003019',
          900: '#00170D',
        },
        warning: {
          50: '#FFF8E1',
          100: '#FFF0B3',
          200: '#FFE185',
          300: '#FFD257',
          400: '#FFC329',
          500: '#E6A800',
          600: '#B88600',
          700: '#8A6500',
          800: '#5C4300',
          900: '#2E2200',
        },
        danger: {
          50: '#FDEDEA',
          100: '#FBDDD9',
          200: '#F7BDB8',
          300: '#F39D97',
          400: '#EF7D76',
          500: '#C41E3A',
          600: '#9D182E',
          700: '#761223',
          800: '#4F0C17',
          900: '#28060C',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains-mono)', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
      },
    },
  },
  plugins: [],
};

export default config;