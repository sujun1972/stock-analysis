/**
 * 用户表单管理 Hook
 */
import { useState } from 'react'
import { toast } from 'sonner'

export interface UserFormData {
  email: string
  username: string
  password: string
  full_name: string
  phone: string
  role: 'super_admin' | 'admin' | 'vip_user' | 'normal_user' | 'trial_user'
  is_email_verified: boolean
}

const initialFormData: UserFormData = {
  email: '',
  username: '',
  password: '',
  full_name: '',
  phone: '',
  role: 'normal_user',
  is_email_verified: false,
}

export function useUserForm() {
  const [formData, setFormData] = useState<UserFormData>(initialFormData)

  // 重置表单
  const resetForm = () => {
    setFormData(initialFormData)
  }

  // 验证邮箱格式
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  /**
   * 验证密码强度
   * 要求：至少8位，包含大小写字母和数字
   */
  const validatePassword = (password: string): { valid: boolean; message: string } => {
    if (password.length < 8) {
      return { valid: false, message: '密码长度至少8位' }
    }
    if (!/[A-Z]/.test(password)) {
      return { valid: false, message: '密码需包含大写字母' }
    }
    if (!/[a-z]/.test(password)) {
      return { valid: false, message: '密码需包含小写字母' }
    }
    if (!/[0-9]/.test(password)) {
      return { valid: false, message: '密码需包含数字' }
    }
    return { valid: true, message: '' }
  }

  // 验证创建表单
  const validateCreateForm = (): boolean => {
    // 验证必填字段
    if (!formData.email || !formData.username || !formData.password) {
      toast.error('请填写所有必填字段')
      return false
    }

    // 验证邮箱格式
    if (!validateEmail(formData.email)) {
      toast.error('请输入有效的邮箱地址')
      return false
    }

    // 验证密码强度
    const passwordValidation = validatePassword(formData.password)
    if (!passwordValidation.valid) {
      toast.error(passwordValidation.message)
      return false
    }

    return true
  }

  // 验证编辑表单
  const validateEditForm = (): boolean => {
    // 验证邮箱格式
    if (formData.email && !validateEmail(formData.email)) {
      toast.error('请输入有效的邮箱地址')
      return false
    }

    // 如果修改了密码，验证密码强度
    if (formData.password) {
      const passwordValidation = validatePassword(formData.password)
      if (!passwordValidation.valid) {
        toast.error(passwordValidation.message)
        return false
      }
    }

    return true
  }

  return {
    formData,
    setFormData,
    resetForm,
    validateEmail,
    validatePassword,
    validateCreateForm,
    validateEditForm,
  }
}
