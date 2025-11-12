/**
 * Toast Component
 * 
 * Purpose: Displays toast notifications to users
 * Features:
 * - Multiple toast messages support
 * - Auto-dismiss after duration
 * - Manual dismiss via close button
 * - Slide-in/out animations
 * - Different styles for success, error, warning, and info types
 * 
 * @author Orbit Skill Development Team
 * @date 2025
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { ToastService, ToastMessage } from '../../services/toast.service';
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  selector: 'app-toast',
  templateUrl: './toast.component.html',
  styleUrls: ['./toast.component.css'],
  animations: [
    trigger('slideInOut', [
      transition(':enter', [
        style({ transform: 'translateX(100%)', opacity: 0 }),
        animate('300ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
      ]),
      transition(':leave', [
        animate('300ms ease-in', style({ transform: 'translateX(100%)', opacity: 0 }))
      ])
    ])
  ]
})
export class ToastComponent implements OnInit, OnDestroy {
  /** Array of active toast messages to display */
  toasts: ToastMessage[] = [];

  /**
   * Component constructor - injects ToastService
   * @param toastService - Service for managing toast notifications
   */
  constructor(private toastService: ToastService) {}

  /**
   * Angular lifecycle hook - subscribes to toast service to receive new toasts
   */
  ngOnInit(): void {
    this.toastService.toasts$.subscribe(toasts => {
      this.toasts = toasts;
    });
  }

  /**
   * Angular lifecycle hook - cleanup
   * Note: Subscription cleanup is handled automatically by Angular
   */
  ngOnDestroy(): void {
    // Cleanup handled by service
  }

  /**
   * Removes a toast message by ID
   * @param id - Unique identifier of the toast to remove
   */
  removeToast(id: string): void {
    this.toastService.remove(id);
  }

  /**
   * Returns the appropriate Font Awesome icon class based on toast type
   * @param type - Toast type: 'success', 'error', 'warning', or 'info'
   * @returns Font Awesome icon class name
   */
  getIconClass(type: string): string {
    switch (type) {
      case 'success': return 'fa-check-circle';
      case 'error': return 'fa-exclamation-circle';
      case 'warning': return 'fa-exclamation-triangle';
      case 'info': return 'fa-info-circle';
      default: return 'fa-bell';
    }
  }

  /**
   * Returns Tailwind CSS classes for toast container based on type
   * @param type - Toast type: 'success', 'error', 'warning', or 'info'
   * @returns Tailwind CSS class string for background, border, and text colors
   */
  getToastClass(type: string): string {
    switch (type) {
      case 'success': return 'bg-green-50 border-green-200 text-green-800';
      case 'error': return 'bg-red-50 border-red-200 text-red-800';
      case 'warning': return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'info': return 'bg-blue-50 border-blue-200 text-blue-800';
      default: return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  }

  /**
   * Returns Tailwind CSS classes for icon color based on toast type
   * @param type - Toast type: 'success', 'error', 'warning', or 'info'
   * @returns Tailwind CSS class string for icon text color
   */
  getIconColorClass(type: string): string {
    switch (type) {
      case 'success': return 'text-green-500';
      case 'error': return 'text-red-500';
      case 'warning': return 'text-yellow-500';
      case 'info': return 'text-blue-500';
      default: return 'text-gray-500';
    }
  }
}
