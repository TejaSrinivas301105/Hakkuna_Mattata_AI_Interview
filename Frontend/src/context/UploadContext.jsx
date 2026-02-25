import { createContext, useContext } from "react";

export const UploadContext = createContext();

export const useUploadStatus = () => useContext(UploadContext);
