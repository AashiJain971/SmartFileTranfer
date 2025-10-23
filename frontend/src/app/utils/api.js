// API client for backend communication
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class FileUploadAPI {
  static async startUpload(fileData) {
    const formData = new FormData();
    formData.append('file_id', fileData.file_id);
    formData.append('filename', fileData.filename);
    formData.append('total_chunks', fileData.total_chunks);
    formData.append('file_size', fileData.file_size);
    formData.append('file_hash', fileData.file_hash);

    const response = await fetch(`${API_BASE_URL}/upload/start`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMessage;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
      } catch {
        errorMessage = `Failed to start upload: ${response.status} ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  static async uploadChunk(chunkData) {
    const formData = new FormData();
    formData.append('file_id', chunkData.file_id);
    formData.append('chunk_number', chunkData.chunk_number);
    formData.append('total_chunks', chunkData.total_chunks);
    formData.append('chunk_hash', chunkData.chunk_hash);
    formData.append('chunk', chunkData.chunk);

    const response = await fetch(`${API_BASE_URL}/upload/chunk`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMessage;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
      } catch {
        errorMessage = `Failed to upload chunk: ${response.status} ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  static async getUploadStatus(fileId) {
    const response = await fetch(`${API_BASE_URL}/upload/status/${fileId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.statusText}`);
    }

    return response.json();
  }

  static async completeUpload(fileId, expectedHash) {
    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('expected_hash', expectedHash);

    const response = await fetch(`${API_BASE_URL}/upload/complete`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to complete upload: ${response.statusText}`);
    }

    return response.json();
  }

  static async cancelUpload(fileId) {
    const response = await fetch(`${API_BASE_URL}/upload/cancel/${fileId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to cancel upload: ${response.statusText}`);
    }

    return response.json();
  }

  static async downloadFile(filename) {
    const response = await fetch(`${API_BASE_URL}/upload/download/${encodeURIComponent(filename)}`);
    
    if (!response.ok) {
      throw new Error(`Failed to download file: ${response.statusText}`);
    }

    return response;
  }

  static async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return response.ok;
    } catch (error) {
      return false;
    }
  }
}