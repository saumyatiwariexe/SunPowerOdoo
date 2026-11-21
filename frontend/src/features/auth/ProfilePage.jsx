import React from 'react'
import { Facts, Heading } from '../../app/records'
import { useAuth } from '../../app/AuthContext'
import { human } from '../../app/navigation'
export default function ProfilePage() {
  const { currentUser } = useAuth()
  return (
    <>
      <Heading title="Staff profile" />
      <Facts
        items={[
          ['Name', currentUser.name],
          ['Email', currentUser.email],
          ['Workspace role', human(currentUser.role)],
          ['Staff ID', currentUser.id],
          ['Phone', currentUser.phone],
        ]}
      />
    </>
  )
}
