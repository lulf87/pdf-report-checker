import { motion } from 'framer-motion';
import { Upload, File } from 'lucide-react';
import { useCallback, useState } from 'react';
import { PULSE_FAST, SPRING_SNAPPY } from '../../constants/motion';
import { GlassCard } from '../ui/GlassCard';

export interface FileUploadFile {
  id: string;
  name: string;
  size: number;
  file: File;
}

interface FileUploadProps {
  onFilesChange: (files: FileUploadFile[]) => void;
  accept?: string;
  multiple?: boolean;
  maxFiles?: number;
  mode?: 'single' | 'double';
  labels?: {
    primary?: string;
    secondary?: string;
  };
  disabled?: boolean;
}

/**
 * FileUpload - Drag and drop file upload component
 *
 * Features:
 * - Drag and drop support
 * - Click to upload
 * - Single or double file mode
 * - File preview with size display
 * - Visual feedback for drag states
 */
export function FileUpload({
  onFilesChange,
  accept = '.pdf',
  multiple = false,
  mode = 'single',
  labels,
  disabled = false,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<FileUploadFile[]>([]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, slotIndex: number) => {
    e.preventDefault();
    setIsDragging(false);

    if (disabled) return;

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf' || file.name.endsWith('.pdf')
    );

    if (droppedFiles.length === 0) return;

    const newFile: FileUploadFile = {
      id: `${Date.now()}-${slotIndex}`,
      name: droppedFiles[0].name,
      size: droppedFiles[0].size,
      file: droppedFiles[0],
    };

    const updatedFiles = [...files];
    if (mode === 'single') {
      updatedFiles[0] = newFile;
    } else {
      updatedFiles[slotIndex] = newFile;
    }

    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  }, [disabled, files, mode, onFilesChange]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>, slotIndex: number) => {
    if (disabled || !e.target.files || e.target.files.length === 0) return;

    const selectedFile = e.target.files[0];
    const newFile: FileUploadFile = {
      id: `${Date.now()}-${slotIndex}`,
      name: selectedFile.name,
      size: selectedFile.size,
      file: selectedFile,
    };

    const updatedFiles = [...files];
    if (mode === 'single') {
      updatedFiles[0] = newFile;
    } else {
      updatedFiles[slotIndex] = newFile;
    }

    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  }, [disabled, files, mode, onFilesChange]);

  const handleRemove = useCallback((slotIndex: number) => {
    if (disabled) return;

    const updatedFiles = [...files];
    updatedFiles[slotIndex] = undefined as any;

    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  }, [disabled, files, onFilesChange]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const uploadSlots = mode === 'single' ? 1 : 2;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        width: '100%',
      }}
    >
      {Array.from({ length: uploadSlots }).map((_, index) => {
        const file = files[index];
        const label = mode === 'double'
          ? (index === 0 ? labels?.primary || '上传检验报告' : labels?.secondary || '上传产品技术要求')
          : labels?.primary || '上传文件';

        return (
          <motion.div
            key={index}
            layout
            transition={SPRING_SNAPPY}
          >
            {file ? (
              /* File Preview */
              <GlassCard>
                <div
                  style={{
                    padding: '1.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                  }}
                >
                  <motion.div
                    style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--glass-bg-hover)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--color-accent)',
                    }}
                    whileHover={{ scale: 1.05 }}
                    transition={SPRING_SNAPPY}
                  >
                    <File size={24} />
                  </motion.div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p
                      style={{
                        fontSize: '1rem',
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {file.name}
                    </p>
                    <p
                      style={{
                        fontSize: '0.875rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {formatFileSize(file.size)}
                    </p>
                  </div>

                  {!disabled && (
                    <motion.button
                      onClick={() => handleRemove(index)}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      transition={SPRING_SNAPPY}
                      style={{
                        padding: '0.5rem',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--glass-bg)',
                        border: '1px solid var(--glass-border)',
                        color: 'var(--color-danger)',
                        cursor: 'pointer',
                      }}
                    >
                      ✕
                    </motion.button>
                  )}
                </div>
              </GlassCard>
            ) : (
              /* Upload Zone */
              <motion.label
                htmlFor={`file-input-${index}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, index)}
                whileHover={disabled ? {} : { scale: 1.01 }}
                whileTap={disabled ? {} : { scale: 0.99 }}
                transition={SPRING_SNAPPY}
                style={{
                  display: 'block',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                }}
              >
                <GlassCard
                  hover={!disabled}
                  style={{
                    padding: '3rem 2rem',
                    textAlign: 'center',
                    borderStyle: 'dashed',
                    background: isDragging
                      ? 'var(--glass-bg-hover)'
                      : 'var(--glass-bg)',
                  }}
                >
                  <motion.div
                    style={{
                      width: '64px',
                      height: '64px',
                      borderRadius: '50%',
                      background: 'var(--glass-bg-hover)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 1.5rem',
                      color: isDragging
                        ? 'var(--color-accent)'
                        : 'var(--text-muted)',
                    }}
                    animate={isDragging ? { scale: [1, 1.1, 1] } : {}}
                    transition={isDragging ? PULSE_FAST : {}}
                  >
                    <Upload size={32} />
                  </motion.div>

                  <p
                    style={{
                      fontSize: '1.125rem',
                      fontWeight: 500,
                      color: 'var(--text-primary)',
                      marginBottom: '0.5rem',
                    }}
                  >
                    {label}
                  </p>

                  <p
                    style={{
                      fontSize: '0.875rem',
                      color: 'var(--text-muted)',
                    }}
                  >
                    拖拽文件到此处或点击上传
                  </p>
                </GlassCard>
              </motion.label>
            )}

            <input
              id={`file-input-${index}`}
              type="file"
              accept={accept}
              multiple={multiple}
              disabled={disabled}
              onChange={(e) => handleFileInput(e, index)}
              style={{ display: 'none' }}
            />
          </motion.div>
        );
      })}
    </div>
  );
}
