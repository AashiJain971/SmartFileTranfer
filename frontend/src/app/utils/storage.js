// Safe localStorage utility with quota management
export class SafeStorage {
  static MAX_FILES = 100; // Maximum number of files to keep in storage
  
  static setItem(key, value) {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (error) {
      if (error.name === 'QuotaExceededError' || error.code === 22) {
        console.warn('localStorage quota exceeded, attempting cleanup...');
        this.cleanupOldEntries(key);
        
        try {
          localStorage.setItem(key, value);
          return true;
        } catch (retryError) {
          console.error('localStorage still full after cleanup:', retryError);
          return false;
        }
      }
      console.error('localStorage error:', error);
      return false;
    }
  }

  static getItem(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.error('localStorage read error:', error);
      return null;
    }
  }

  static cleanupOldEntries(key) {
    try {
      if (key === 'uploadedFiles') {
        const files = JSON.parse(this.getItem('uploadedFiles') || '[]');
        
        // Sort by upload date (newest first) and keep only the latest entries
        files.sort((a, b) => new Date(b.uploadDate) - new Date(a.uploadDate));
        const trimmedFiles = files.slice(0, this.MAX_FILES);
        
        // Try to store the trimmed list
        this.forceSetItem('uploadedFiles', JSON.stringify(trimmedFiles));
        
        console.log(`Cleaned up file list: ${files.length} -> ${trimmedFiles.length} files`);
      }
    } catch (error) {
      console.error('Cleanup failed:', error);
      // If cleanup fails, clear the storage completely
      this.clearItem(key);
    }
  }

  static forceSetItem(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      // If it still fails, clear the item completely
      localStorage.removeItem(key);
      localStorage.setItem(key, value);
    }
  }

  static clearItem(key) {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Failed to clear localStorage item:', error);
    }
  }

  static addUploadedFile(fileInfo) {
    try {
      const files = JSON.parse(this.getItem('uploadedFiles') || '[]');
      
      // Remove any existing file with the same name to avoid duplicates
      const filteredFiles = files.filter(f => f.name !== fileInfo.name);
      
      // Add the new file at the beginning (most recent first)
      filteredFiles.unshift({
        name: fileInfo.name,
        size: fileInfo.size,
        uploadDate: new Date().toISOString(),
        fileId: fileInfo.fileId
      });

      // Limit the number of files to prevent storage overflow
      const limitedFiles = filteredFiles.slice(0, this.MAX_FILES);
      
      const success = this.setItem('uploadedFiles', JSON.stringify(limitedFiles));
      
      if (!success) {
        throw new Error('Failed to save file to storage');
      }
      
      return true;
    } catch (error) {
      console.error('Failed to add uploaded file:', error);
      throw new Error('Could not save file information. Storage may be full.');
    }
  }

  static removeUploadedFile(fileName) {
    try {
      const files = JSON.parse(this.getItem('uploadedFiles') || '[]');
      const filteredFiles = files.filter(f => f.name !== fileName);
      
      const success = this.setItem('uploadedFiles', JSON.stringify(filteredFiles));
      return success;
    } catch (error) {
      console.error('Failed to remove uploaded file:', error);
      return false;
    }
  }

  static getUploadedFiles() {
    try {
      return JSON.parse(this.getItem('uploadedFiles') || '[]');
    } catch (error) {
      console.error('Failed to get uploaded files:', error);
      return [];
    }
  }

  static getStorageInfo() {
    let used = 0;
    try {
      for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key)) {
          used += localStorage[key].length + key.length;
        }
      }
    } catch (error) {
      console.error('Failed to calculate storage usage:', error);
    }
    
    return {
      used: used,
      usedMB: (used / (1024 * 1024)).toFixed(2),
      // Most browsers limit localStorage to 5-10MB
      estimatedLimit: '5-10MB'
    };
  }
}