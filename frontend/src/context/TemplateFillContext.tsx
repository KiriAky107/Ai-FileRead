import React, { createContext, useContext, useState, ReactNode } from 'react';

type SourceFile = {
  file: File;
  preview?: string;
};

type TemplateField = {
  cell: string;
  name: string;
  field_type: string;
  required: boolean;
  hint?: string;
};

type Step = 'upload' | 'filling' | 'preview';

interface TemplateFillState {
  step: Step;
  templateFile: File | null;
  templateFields: TemplateField[];
  sourceFiles: SourceFile[];
  sourceFilePaths: string[];
  templateId: string;
  filledResult: any;
  setStep: (step: Step) => void;
  setTemplateFile: (file: File | null) => void;
  setTemplateFields: (fields: TemplateField[]) => void;
  setSourceFiles: (files: SourceFile[]) => void;
  addSourceFiles: (files: SourceFile[]) => void;
  removeSourceFile: (index: number) => void;
  setSourceFilePaths: (paths: string[]) => void;
  setTemplateId: (id: string) => void;
  setFilledResult: (result: any) => void;
  reset: () => void;
}

const initialState = {
  step: 'upload' as Step,
  templateFile: null,
  templateFields: [],
  sourceFiles: [],
  sourceFilePaths: [],
  templateId: '',
  filledResult: null,
  setStep: () => {},
  setTemplateFile: () => {},
  setTemplateFields: () => {},
  setSourceFiles: () => {},
  addSourceFiles: () => {},
  removeSourceFile: () => {},
  setSourceFilePaths: () => {},
  setTemplateId: () => {},
  setFilledResult: () => {},
  reset: () => {},
};

const TemplateFillContext = createContext<TemplateFillState>(initialState);

export const TemplateFillProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [step, setStep] = useState<Step>('upload');
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [templateFields, setTemplateFields] = useState<TemplateField[]>([]);
  const [sourceFiles, setSourceFiles] = useState<SourceFile[]>([]);
  const [sourceFilePaths, setSourceFilePaths] = useState<string[]>([]);
  const [templateId, setTemplateId] = useState<string>('');
  const [filledResult, setFilledResult] = useState<any>(null);

  const addSourceFiles = (files: SourceFile[]) => {
    setSourceFiles(prev => [...prev, ...files]);
  };

  const removeSourceFile = (index: number) => {
    setSourceFiles(prev => prev.filter((_, i) => i !== index));
  };

  const reset = () => {
    setStep('upload');
    setTemplateFile(null);
    setTemplateFields([]);
    setSourceFiles([]);
    setSourceFilePaths([]);
    setTemplateId('');
    setFilledResult(null);
  };

  return (
    <TemplateFillContext.Provider
      value={{
        step,
        templateFile,
        templateFields,
        sourceFiles,
        sourceFilePaths,
        templateId,
        filledResult,
        setStep,
        setTemplateFile,
        setTemplateFields,
        setSourceFiles,
        addSourceFiles,
        removeSourceFile,
        setSourceFilePaths,
        setTemplateId,
        setFilledResult,
        reset,
      }}
    >
      {children}
    </TemplateFillContext.Provider>
  );
};

export const useTemplateFill = () => useContext(TemplateFillContext);
