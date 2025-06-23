# SharePoint Index Selection Enhancement

## 🎯 **New Feature: Direct Index Selection in SharePoint Tab**

### **Overview**
Added the ability for users to select the target index directly within the SharePoint Index tab, eliminating the need to navigate to the "Manage Index" tab for SharePoint-specific indexing operations.

## 🚀 **Features Implemented**

### **1. SharePoint-Specific Index Selection**
- **Dedicated Index Selector**: New dropdown in the SharePoint configuration section
- **Independent Selection**: Can choose different indexes for SharePoint vs. other operations
- **Smart Defaults**: Automatically syncs with global index selection when appropriate

### **2. Dual Index Management**
- **SharePoint Target Index**: `st.session_state.sp_target_index`
- **Global Index**: `st.session_state.selected_index` (unchanged)
- **Priority Logic**: SharePoint-specific index takes precedence for SharePoint operations

### **3. Visual Status Indicators**
- **Target Index Display**: Clear indication of selected index with source
- **Status Icons**: ✅ for selected, ⚠️ for not selected
- **Index Source Labels**: "SharePoint-specific" vs "Global" selection

### **4. Synchronization Controls**
- **"Set as Global Index" Button**: Promotes SharePoint index to global selection
- **"Use Global Index" Button**: Uses global index for SharePoint operations
- **Smart Fallback**: Automatically uses global index if SharePoint-specific not set

## 🎨 **User Interface**

### **Configuration Section Layout**
```
🔧 SharePoint Configuration
┌─────────────────────────────────────────────────────────────┐
│ Site Domain          │ Drive/Library Name                   │
│ Site Name            │ File Types                           │
└─────────────────────────────────────────────────────────────┘

🎯 Target Index Selection
┌─────────────────────────────────────────────────────────────┐
│ Select Target Index: [Dropdown]     │ ✅ Target Index      │
│                                      │ my-sharepoint-index   │
│                                      │ [🔄 Set as Global]   │
└─────────────────────────────────────────────────────────────┘
```

### **Index Selection Dropdown**
- **Options**: "Select an index..." + all available indexes
- **Current Selection**: Highlights currently selected index
- **Help Text**: "Choose the search index where SharePoint documents will be stored"

### **Status Panel Features**
- **Selected State**: Shows index name with checkmark
- **Unselected State**: Shows warning with suggestions
- **Action Buttons**: Quick sync between SharePoint and global selections

## 🔧 **Technical Implementation**

### **Session State Variables**
```python
# New SharePoint-specific index selection
st.session_state.sp_target_index = "my-sharepoint-index"

# Existing global index selection (unchanged)
st.session_state.selected_index = "global-index"

# Available indexes (shared)
st.session_state.available_indexes = ["index1", "index2", ...]
```

### **Index Resolution Logic**
```python
# Determine target index with priority
target_index = (
    getattr(st.session_state, 'sp_target_index', None) or 
    st.session_state.selected_index
)
```

### **Synchronization Functions**
- **Set as Global**: `st.session_state.selected_index = st.session_state.sp_target_index`
- **Use Global**: `st.session_state.sp_target_index = st.session_state.selected_index`

## 📊 **User Workflow Improvements**

### **Before (Required Navigation)**
1. Go to "Manage Index" tab
2. Select/create target index
3. Navigate to "SharePoint Index" tab
4. Configure and run indexing

### **After (Streamlined Workflow)**
1. Go to "SharePoint Index" tab
2. Select target index directly in the tab
3. Configure and run indexing immediately
4. Optional: Sync with global index as needed

## 🎯 **Benefits**

### **User Experience**
- **Faster Workflow**: Eliminate tab switching for index selection
- **Context Awareness**: Select index while configuring SharePoint settings
- **Flexibility**: Use different indexes for different SharePoint sites
- **Visual Clarity**: Always know which index will be used

### **Operational Efficiency**
- **Reduced Clicks**: Fewer navigation steps required
- **Error Prevention**: Clear indication of target index before indexing
- **Workflow Flexibility**: Support for multiple concurrent index strategies
- **Backward Compatibility**: Existing "Manage Index" functionality unchanged

### **Advanced Use Cases**
- **Multi-Site Indexing**: Different indexes for different SharePoint sites
- **Environment Separation**: Separate dev/test/prod indexes
- **Content Categorization**: Different indexes for different content types
- **Team Workflows**: Team-specific index selection

## 🚦 **Usage Examples**

### **Scenario 1: Quick SharePoint Indexing**
```
1. User opens SharePoint Index tab
2. Selects "sharepoint-docs" from index dropdown
3. Configures folders and runs indexing
4. Documents indexed to "sharepoint-docs" index
```

### **Scenario 2: Sync with Global Selection**
```
1. User has "main-index" selected globally
2. Clicks "Use Global Index" in SharePoint tab
3. SharePoint operations now use "main-index"
4. Consistent indexing across all tabs
```

### **Scenario 3: Promote SharePoint Index**
```
1. User selects "best-index" for SharePoint
2. Clicks "Set as Global Index"
3. "best-index" becomes global selection
4. All tabs now use "best-index" by default
```

## 🔄 **Backward Compatibility**

- **Existing Functionality**: "Manage Index" tab works exactly as before
- **Global Selection**: Existing global index selection logic preserved
- **Fallback Behavior**: SharePoint operations fall back to global index if no specific selection
- **Session State**: No breaking changes to existing session state variables

This enhancement significantly improves the user experience for SharePoint indexing operations while maintaining full compatibility with existing functionality.
