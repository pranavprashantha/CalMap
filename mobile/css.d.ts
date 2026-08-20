/// <reference types="nativewind/types" />

// The Expo template imports CSS for web styling, which TypeScript has no knowledge of
// without these declarations. Kept separate from expo-env.d.ts, which Expo regenerates.
declare module '*.module.css' {
  const classes: Record<string, string>;
  export default classes;
}

declare module '*.css';
